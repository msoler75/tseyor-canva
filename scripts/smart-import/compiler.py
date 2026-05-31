"""
SmartImportCompiler — deterministic SceneGraph → .tc v2 compiler.

Transforms a validated SceneGraph (from ``validator.py``) into a Tseyor Canva
.tc v2 structure ready to save as JSON.  Handles text/image/shape layers,
background mapping, image asset cropping (Pillow), heuristic content-key
assignment, and incremental z-indexing.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
from typing import Optional

from PIL import Image

from image_utils import region_to_data_uri

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTENT_KEYS = ("title", "subtitle", "meta", "contact", "extra")
SUPPORTED_MODES = {"text_only", "basic_image_layers"}
BASIC_IMAGE_LAYER_CONFIDENCE_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class SmartImportCompiler:
    """Compiles a validated SceneGraph into a .tc v2 structure.

    Usage::

        compiler = SmartImportCompiler()
        tc = compiler.compile(scene, "path/to/source.jpg")
        compiler.export(tc, "output/design.tc")
    """

    def __init__(self, mode: str = "basic_image_layers"):
        if mode not in SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported Smart Import mode: {mode}. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_MODES))}"
            )
        self.mode = mode

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def compile(self, scene: dict, source_image: str) -> dict:
        """Transform a validated SceneGraph into a .tc v2 dict.

        Parameters
        ----------
        scene:
            Validated SceneGraph — the ``fixed`` output from
            ``validator.validate_scene()``.
        source_image:
            Filesystem path to the original source image.  Used to
            crop image-layer assets.

        Returns
        -------
        dict
            A structure that can be serialised as .tc JSON and,
            with some caveats, imported into the Tseyor Canva editor.
        """
        canvas = scene.get("canvas", {})
        width = canvas.get("width", 1080)
        height = canvas.get("height", 1350)
        detected_format = canvas.get("detectedFormat", "vertical")
        layers = self._filter_layers_for_mode(scene.get("layers", []))
        background = scene.get("background")

        # Build the three page-level sections
        content = self._assign_content_keys(layers)
        element_layout = self._build_element_layout(layers, background)
        custom_elements = self._build_custom_elements(layers, source_image)

        tc: dict = {
            "tcVersion": 2,
            "designSurface": {"width": width, "height": height},
            "format": detected_format,
            "size": f"{width} \u00d7 {height} px",
            "pages": [
                {
                    "id": "smart-page-1",
                    "content": content,
                    "elementLayout": element_layout,
                    "customElements": custom_elements,
                }
            ],
        }
        return tc

    def _filter_layers_for_mode(self, layers: list[dict]) -> list[dict]:
        """Return the subset of layers supported by the configured V1 mode."""
        filtered: list[dict] = []
        for layer in layers:
            if not isinstance(layer, dict):
                continue

            kind = layer.get("kind")
            if self.mode == "text_only":
                if kind == "text":
                    filtered.append(layer)
                continue

            confidence = layer.get("confidence", 0)
            if confidence is None or confidence < BASIC_IMAGE_LAYER_CONFIDENCE_THRESHOLD:
                continue
            filtered.append(layer)

        return filtered

    # ---------------------------------------------------------------
    # Content helpers
    # ---------------------------------------------------------------

    def _assign_content_keys(self, layers: list[dict]) -> dict:
        """Heuristically assign text layers to ``content`` keys.

        Sorts text layers by visual prominence (area × fontSize ×
        confidence, then top-to-bottom), and maps them to
        ``title / subtitle / meta / contact / extra``.

        Returns a dict with up to 5 keys, each mapped to the
        layer's ``text`` content.
        """
        text_layers = [l for l in layers if l.get("kind") == "text"]
        if not text_layers:
            return {}

        def _score(layer: dict) -> tuple:
            """Score visual prominence — higher = more important."""
            bbox = layer.get("bbox", {}) or {}
            w = bbox.get("w", 0) or 0
            h = bbox.get("h", 0) or 0
            area = w * h
            style = layer.get("style") or {}
            font_size = style.get("fontSize", 12) or 12
            confidence = layer.get("confidence", 0.5) or 0.5
            # Negative y so higher-positioned text sorts first
            y = bbox.get("y", 0) or 0
            return (area * font_size * confidence, -y)

        sorted_layers = sorted(text_layers, key=_score, reverse=True)

        content: dict[str, str] = {}
        for i, layer in enumerate(sorted_layers):
            if i >= len(_CONTENT_KEYS):
                break
            text = layer.get("text", "")
            if text:
                content[_CONTENT_KEYS[i]] = text
        return content

    def _map_confidence_label(self, confidence: float) -> str:
        """Map a numeric confidence score to a human-readable label.

        =========  =======
        Range      Label
        =========  =======
        > 0.8      ``"high"``
        > 0.5      ``"medium"``
        ≤ 0.5      ``"low"``
        =========  =======
        """
        if confidence > 0.8:
            return "high"
        elif confidence > 0.5:
            return "medium"
        return "low"

    # ---------------------------------------------------------------
    # Element layout (position + z-index)
    # ---------------------------------------------------------------

    def _build_element_layout(
        self, layers: list[dict], background: Optional[dict]
    ) -> dict:
        """Build the ``elementLayout`` dict.

        Returns ``{"background": {...}, "layer-1": {...}, ...}``.

        - Background entry always includes ``zIndex: 0``.
        - Each layer entry gets ``x``, ``y``, ``w``, ``h``, ``zIndex``.
        - zIndex increments by layer order; background sits at 0.
        """
        layout: dict = {}

        # --- Background (zIndex 0) ---
        if background:
            bg_layout: dict = {"zIndex": 0}
            kind = background.get("kind", "solid")
            if kind == "gradient":
                grad = background.get("gradient") or {}
                stops = grad.get("stops") or []
                bg_layout["fillMode"] = "gradient"
                if len(stops) >= 1:
                    bg_layout["gradientStart"] = stops[0].get("color", "#000000")
                if len(stops) >= 2:
                    bg_layout["gradientEnd"] = stops[-1].get("color", "#ffffff")
                else:
                    bg_layout["gradientEnd"] = stops[0].get("color", "#000000") if stops else "#ffffff"
                bg_layout["gradientAngle"] = grad.get("angle", 180)
            else:
                # solid or image kind — use backgroundColor
                bg_layout["backgroundColor"] = background.get("color", "#ffffff")
            layout["background"] = bg_layout

        # --- Layers (zIndex 1+) ---
        z_offset = 1 if background else 0
        for i, layer in enumerate(layers):
            layer_id = layer.get("id", f"layer-{i}")
            bbox = layer.get("bbox") or {}
            layout[layer_id] = {
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "w": bbox.get("w", 0),
                "h": bbox.get("h", 0),
                "zIndex": z_offset + i,
            }

        return layout

    # ---------------------------------------------------------------
    # Custom elements (type & styling)
    # ---------------------------------------------------------------

    def _build_custom_elements(
        self, layers: list[dict], source_image: str
    ) -> dict:
        """Build the ``customElements`` dict from SceneGraph layers.

        Routes each layer to a type-specific builder:
        ``_build_text_element``, ``_build_image_element``, or
        ``_build_shape_element``.
        """
        elements: dict = {}
        for i, layer in enumerate(layers):
            layer_id = layer.get("id", f"layer-{i}")
            kind = layer.get("kind", "shape")

            if kind == "text":
                elements[layer_id] = self._build_text_element(layer)
            elif kind == "image":
                elements[layer_id] = self._build_image_element(
                    layer, source_image
                )
            elif kind == "shape":
                elements[layer_id] = self._build_shape_element(layer)

        return elements

    def _build_text_element(self, layer: dict) -> dict:
        """Build a text custom element from a SceneGraph text layer.

        Maps style properties: ``fontSize``, ``fontWeight``,
        ``color``, ``textAlign``.  Stores the layer text as both
        ``text`` and ``html`` for compatibility.
        """
        style = layer.get("style") or {}
        elem: dict = {
            "type": "text",
            "text": layer.get("text", ""),
            "html": layer.get("text", ""),
        }

        if "fontSize" in style and style["fontSize"]:
            elem["fontSize"] = style["fontSize"]
        if "fontWeight" in style and style["fontWeight"]:
            elem["fontWeight"] = self._map_weight(style["fontWeight"])
        if "color" in style and style["color"]:
            elem["color"] = style["color"]
        if "textAlign" in style and style["textAlign"]:
            elem["textAlign"] = style["textAlign"]

        return elem

    def _build_image_element(self, layer: dict, source_image: str) -> dict:
        """Build an image custom element from a SceneGraph image layer.

        Crops the source image using the layer's bounding box, encodes
        the crop as a base64 data URI, and records intrinsic dimensions.
        """
        elem: dict = {
            "type": "image",
            "uploadStatus": "pending",
            "needsUpload": True,
        }

        bbox = layer.get("bbox") or {}
        if source_image and os.path.isfile(source_image):
            data_uri = region_to_data_uri(source_image, bbox)
            if data_uri:
                elem["src"] = data_uri
                # Derive intrinsic dimensions from the cropped image
                try:
                    header, encoded = data_uri.split(",", 1)
                    img_data = base64.b64decode(encoded)
                    with Image.open(io.BytesIO(img_data)) as img:
                        elem["intrinsicWidth"] = img.width
                        elem["intrinsicHeight"] = img.height
                except Exception as exc:
                    logger.warning(
                        "Could not decode cropped image for %s: %s",
                        layer.get("id", "?"), exc,
                    )
                    elem["intrinsicWidth"] = bbox.get("w", 0)
                    elem["intrinsicHeight"] = bbox.get("h", 0)

        return elem

    def _build_shape_element(self, layer: dict) -> dict:
        """Build a shape custom element from a SceneGraph shape layer."""
        shape_kind = layer.get("shape", "rectangle")
        elem: dict = {
            "type": "shape",
            "shapeKind": shape_kind,
        }

        shape_style = layer.get("shapeStyle")
        if isinstance(shape_style, dict):
            if "fill" in shape_style:
                elem["fillColor"] = shape_style["fill"]
            if "opacity" in shape_style:
                elem["opacity"] = shape_style["opacity"]
            if "borderRadius" in shape_style:
                elem["borderRadius"] = shape_style["borderRadius"]

        return elem

    # ---------------------------------------------------------------
    # Image cropping (delegates to ``image_utils``)
    # ---------------------------------------------------------------

    def _crop_image(self, source_path: str, bbox: dict) -> str:
        """Crop a region — delegates to :func:`image_utils.region_to_data_uri`."""
        return region_to_data_uri(source_path, bbox)

    # ---------------------------------------------------------------
    # Style mapping helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _map_font(category: str) -> str:
        """Map a font category to an app-available font family.

        The app's standard fonts are Montserrat (display / serif)
        and Manrope (sans-serif / monospace).
        """
        mapping = {
            "serif": "Montserrat",
            "sans-serif": "Manrope",
            "display": "Montserrat",
            "handwriting": "Montserrat",
            "monospace": "Manrope",
        }
        return mapping.get(category, "Manrope")

    @staticmethod
    def _map_align(align: str) -> str:
        """Normalise a text alignment value.

        Accepted: ``left``, ``center``, ``right``, ``justify``.
        Falls back to ``"left"``.
        """
        valid = {"left", "center", "right", "justify"}
        return align if align in valid else "left"

    @staticmethod
    def _map_weight(weight: str) -> str:
        """Normalise font weight to app-supported values.

        Returns one of ``"bold"``, ``"medium"``, or ``"regular"``.
        Handles both numeric (100-900) and named values.
        """
        if not weight:
            return "regular"

        w = weight.strip().lower()

        # Numeric CSS weights
        numeric: dict[str, str] = {
            "100": "regular",
            "200": "regular",
            "300": "regular",
            "400": "regular",
            "500": "medium",
            "600": "medium",
            "700": "bold",
            "800": "bold",
            "900": "bold",
        }
        if w in numeric:
            return numeric[w]

        # Named weights
        if w in ("bold", "bolder", "700", "800", "900"):
            return "bold"
        if w in ("medium", "semibold", "semi-bold", "500", "600"):
            return "medium"

        return "regular"

    # ---------------------------------------------------------------
    # Export
    # ---------------------------------------------------------------

    @staticmethod
    def export(tc: dict, path: str) -> None:
        """Write a .tc dict to a JSON file on disk.

        Creates parent directories as needed.
        """
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tc, f, indent=2, ensure_ascii=False)

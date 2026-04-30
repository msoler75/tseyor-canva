import axios from 'axios';

/**
 * Composable para enviar logs del frontend al backend de Laravel.
 * Los logs se acumulan y se envían en batch para minimizar llamadas HTTP.
 */

const LOG_ENDPOINT = '/api/logs';
const MAX_QUEUE_SIZE = 50;
const FLUSH_DEBOUNCE = 1500; // 1.5 segundos de debounce tras el último log

let logQueue = [];
let flushTimer = null;

/**
 * Enviar un log individual al backend (acumulado en cola).
 */
function sendLog(level, category, message, data = {}) {
  const logEntry = {
    level,
    category,
    message,
    data: serializeData(data),
    timestamp: new Date().toISOString(),
  };

  logQueue.push(logEntry);

  // Si la cola está llena, flush inmediato
  if (logQueue.length >= MAX_QUEUE_SIZE) {
    flushLogs();
    return;
  }

  // Resetear el debounce timer cada vez que llega un log nuevo
  if (flushTimer) {
    clearTimeout(flushTimer);
  }
  flushTimer = setTimeout(flushLogs, FLUSH_DEBOUNCE);
}

/**
 * Enviar todos los logs pendientes al backend en UNA sola llamada.
 */
async function flushLogs() {
  if (logQueue.length === 0) return;

  const logsToSend = [...logQueue];
  logQueue = [];

  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }

  try {
    await axios.post(LOG_ENDPOINT, { logs: logsToSend });
  } catch (error) {
    // Si falla, devolver a la cola (pero no infinitamente)
    if (logQueue.length < MAX_QUEUE_SIZE * 2) {
      logQueue = [...logsToSend, ...logQueue];
    }
  }
}

/**
 * Serializar datos complejos para el backend.
 */
function serializeData(data) {
  if (!data || typeof data !== 'object') {
    return { value: String(data) };
  }

  const serialized = {};
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) {
      serialized[key] = String(value);
    } else if (typeof value === 'object') {
      try {
        serialized[key] = JSON.stringify(value);
      } catch {
        serialized[key] = '[Object no serializable]';
      }
    } else {
      serialized[key] = String(value);
    }
  }
  return serialized;
}

/**
 * API pública del composable.
 */
export function useFrontendLog() {
  const debug = (category, message, data) => sendLog('debug', category, message, data);
  const info = (category, message, data) => sendLog('info', category, message, data);
  const warning = (category, message, data) => sendLog('warning', category, message, data);
  const error = (category, message, data) => sendLog('error', category, message, data);

  const logLinkedTextStyleComparison = (boxId, displayStyles, editStyles, metadata = {}) => {
    const differences = compareStyles(displayStyles, editStyles);
    
    const logData = {
      boxId,
      displayStyles: displayStyles || {},
      editStyles: editStyles || {},
      differences,
      hasDifferences: differences.length > 0,
      metadata,
    };

    if (differences.length > 0) {
      warning('linked-text-styles', 
        `Diferencias de estilo detectadas en caja ${boxId}`, 
        logData
      );
    } else {
      info('linked-text-styles', 
        `Estilos idénticos en caja ${boxId}`, 
        logData
      );
    }

    return logData;
  };

  const logElementStyles = (boxId, mode, element, computedStyles) => {
    const styles = extractRelevantStyles(computedStyles);
    
    info('element-styles', 
      `Estilos CSS en modo ${mode} para ${boxId}`, 
      {
        boxId,
        mode,
        elementTag: element?.tagName,
        elementClasses: element?.className,
        styles,
        html: element?.outerHTML?.substring(0, 500),
      }
    );

    return styles;
  };

  const logFragmentation = (groupId, boxId, fragmentData) => {
    info('fragmentation', 
      `Fragmento para caja ${boxId} en grupo ${groupId}`, 
      {
        groupId,
        boxId,
        fragmentHtml: fragmentData.html?.substring(0, 500),
        overflowHtml: fragmentData.overflowHtml?.substring(0, 500),
        fitsInBox: fragmentData.fitsInBox,
        htmlLength: fragmentData.html?.length || 0,
        overflowLength: fragmentData.overflowHtml?.length || 0,
      }
    );
  };

  const logMeasurement = (boxId, containerStyles, measuredHeight, frameHeight) => {
    debug('measurement', 
      `Medición para caja ${boxId}`, 
      {
        boxId,
        containerStyles,
        measuredHeight,
        frameHeight,
        fitsInFrame: measuredHeight <= frameHeight,
        overflowPixels: Math.max(0, measuredHeight - frameHeight),
      }
    );
  };

  const flush = flushLogs;

  return {
    debug,
    info,
    warning,
    error,
    logLinkedTextStyleComparison,
    logElementStyles,
    logFragmentation,
    logMeasurement,
    flush,
  };
}

function extractRelevantStyles(computedStyles) {
  if (!computedStyles) return {};

  const relevantProperties = [
    'fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'lineHeight',
    'letterSpacing', 'wordSpacing', 'textTransform', 'textAlign', 'color',
    'backgroundColor', 'padding', 'margin', 'border', 'borderRadius',
    'boxSizing', 'width', 'height', 'overflow', 'whiteSpace', 'wordBreak',
    'overflowWrap', 'textDecoration', 'textShadow', 'textIndent',
  ];

  const styles = {};
  for (const prop of relevantProperties) {
    if (computedStyles[prop] !== undefined) {
      styles[prop] = computedStyles[prop];
    }
  }

  return styles;
}

function compareStyles(displayStyles, editStyles) {
  if (!displayStyles || !editStyles) return [];

  const differences = [];
  const allKeys = new Set([
    ...Object.keys(displayStyles),
    ...Object.keys(editStyles),
  ]);

  for (const key of allKeys) {
    const displayValue = displayStyles[key];
    const editValue = editStyles[key];

    if (displayValue !== editValue) {
      differences.push({
        property: key,
        displayValue: displayValue ?? '[no definido]',
        editValue: editValue ?? '[no definido]',
      });
    }
  }

  return differences;
}

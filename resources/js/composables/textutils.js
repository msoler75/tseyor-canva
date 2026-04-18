// remove accents and optionally remove regional characters
export const removeAccents = function (str, regional) {
    if(!str) return ""
  var mapAccents = {
    a: "á|à|ã|â",
    e: "é|è|ê",
    i: "í|ì|î",
    o: "ó|ò|ô|õ",
    u: "ú|ù|û|ü",
    A: "À|Á|Ã|Â",
    E: "É|È|Ê",
    I: "Í|Ì|Î",
    O: "Ó|Ò|Ô|Õ",
    U: "Ú|Ù|Û|Ü",
  };

  var mapRegional = {
    c: "ç",
    n: "ñ",
    C: "Ç",
    N: "Ñ",
  };

  for (var pattern in mapAccents) {
    str = str.replace(new RegExp(mapAccents[pattern], "g"), pattern);
  }

  if (regional)
    for (var pattern in mapRegional) {
      str = str.replace(new RegExp(mapRegional[pattern], "g"), pattern);
    }

  return str;
};

// capitalize each word
export const ucFirstAllWords = function (str) {
  var pieces = str.split(" ");
  for (var i = 0; i < pieces.length; i++) {
    var j = pieces[i].charAt(0).toUpperCase();
    pieces[i] = j + pieces[i].substr(1).toLowerCase();
  }
  return pieces.join(" ");
};

//  capitalize first letter of str
export const ucFirst = function (str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// build initials from name and surname
export const initials = function (name) {
  const parts = name
    .toUpperCase()
    .split(" ")
    .filter((w) => !["LA", "DE", "PM"].includes(w.toLowerCase()))
    .slice(0, 5);

  var str = "";
  parts.forEach((part) => {
    str += part.charAt(0);
  });
  return str;
};


export const plural = function (count, label) {
    return `${count} ${label + (count != 1 ? 's' : '')}`
}


export function levenshtein(s, t) {
    if (s === t) {
        return 0;
    }
    var n = s.length, m = t.length;
    if (n === 0 || m === 0) {
        return n + m;
    }
    var x = 0, y, a, b, c, d, g, h, k;
    var p = new Array(n);
    for (y = 0; y < n;) {
        p[y] = ++y;
    }

    for (; (x + 3) < m; x += 4) {
        var e1 = t.charCodeAt(x);
        var e2 = t.charCodeAt(x + 1);
        var e3 = t.charCodeAt(x + 2);
        var e4 = t.charCodeAt(x + 3);
        c = x;
        b = x + 1;
        d = x + 2;
        g = x + 3;
        h = x + 4;
        for (y = 0; y < n; y++) {
            k = s.charCodeAt(y);
            a = p[y];
            if (a < c || b < c) {
                c = (a > b ? b + 1 : a + 1);
            }
            else {
                if (e1 !== k) {
                    c++;
                }
            }

            if (c < b || d < b) {
                b = (c > d ? d + 1 : c + 1);
            }
            else {
                if (e2 !== k) {
                    b++;
                }
            }

            if (b < d || g < d) {
                d = (b > g ? g + 1 : b + 1);
            }
            else {
                if (e3 !== k) {
                    d++;
                }
            }

            if (d < g || h < g) {
                g = (d > h ? h + 1 : d + 1);
            }
            else {
                if (e4 !== k) {
                    g++;
                }
            }
            p[y] = h = g;
            g = d;
            d = b;
            b = c;
            c = a;
        }
    }

    for (; x < m;) {
        var e = t.charCodeAt(x);
        c = x;
        d = ++x;
        for (y = 0; y < n; y++) {
            a = p[y];
            if (a < c || d < c) {
                d = (a > d ? d + 1 : a + 1);
            }
            else {
                if (e !== s.charCodeAt(y)) {
                    d = c + 1;
                }
                else {
                    d = c;
                }
            }
            p[y] = d;
            c = a;
        }
        h = d;
    }

    return h;
}



export default function truncateText(text, maxLength = 512) {
  if (!text) return '';
  const paragraphs = text.split('\n');
  let result = '';
  let length = 0;
  for (const para of paragraphs) {
    if (length + para.length > maxLength) {
      if (result === '') {
        return para.substring(0, maxLength) + '...';
      }
      break;
    }
    result += para + '\n';
    length += para.length;
  }
  return result.trim();
}

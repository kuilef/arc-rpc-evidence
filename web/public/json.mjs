// Duplicate-key, nonfinite-number and depth checks preserve the CLI envelope boundary.
export function parseStrict(text, validateNumber = () => {}) {
  let i = 0;
  const space = () => { while (/[ \t\r\n]/.test(text[i] ?? "") && i < text.length) i++; };
  function string() {
    const start = i++;
    while (i < text.length) {
      const c = text[i++];
      if (c === '"') return JSON.parse(text.slice(start, i));
      if (c === "\\") i++;
    }
    throw Error("invalid_json");
  }
  function value(depth = 0, path = []) {
    if (depth > 64) throw Error("json_depth_limit");
    space();
    const c = text[i];
    if (c === '"') return string();
    if (c === "{") {
      i++; space(); const out = Object.create(null), seen = new Set();
      if (text[i] === "}") { i++; return out; }
      for (;;) {
        space(); if (text[i] !== '"') throw Error("invalid_json");
        const key = string(); if (seen.has(key)) throw Error("duplicate_json_key"); seen.add(key);
        space(); if (text[i++] !== ":") throw Error("invalid_json");
        out[key] = value(depth + 1, [...path, key]); space();
        const next = text[i++]; if (next === "}") return out;
        if (next !== ",") throw Error("invalid_json");
      }
    }
    if (c === "[") {
      i++; space(); const out = [];
      if (text[i] === "]") { i++; return out; }
      for (;;) {
        out.push(value(depth + 1, [...path, out.length])); space();
        const next = text[i++]; if (next === "]") return out;
        if (next !== ",") throw Error("invalid_json");
      }
    }
    for (const [token, result] of [["true", true], ["false", false], ["null", null]]) {
      if (text.startsWith(token, i)) { i += token.length; return result; }
    }
    const match = text.slice(i).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (!match) throw Error("invalid_json");
    i += match[0].length; const result = Number(match[0]);
    if (!Number.isFinite(result) || (Number.isInteger(result) && !Number.isSafeInteger(result))) throw Error("unsupported_json_number");
    validateNumber(result, match[0], path);
    return result;
  }
  const result = value(); space();
  if (i !== text.length) throw Error("invalid_json");
  return result;
}

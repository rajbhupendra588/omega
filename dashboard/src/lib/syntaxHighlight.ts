import hljs from "highlight.js/lib/core";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import go from "highlight.js/lib/languages/go";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import kotlin from "highlight.js/lib/languages/kotlin";
import php from "highlight.js/lib/languages/php";
import python from "highlight.js/lib/languages/python";
import ruby from "highlight.js/lib/languages/ruby";
import rust from "highlight.js/lib/languages/rust";
import scala from "highlight.js/lib/languages/scala";
import typescript from "highlight.js/lib/languages/typescript";

const registered = new Set<string>();

function ensureLanguage(lang: string): string {
  const id = lang.toLowerCase();
  if (registered.has(id)) return id;
  const map: Record<string, () => void> = {
    python: () => hljs.registerLanguage("python", python),
    java: () => hljs.registerLanguage("java", java),
    go: () => hljs.registerLanguage("go", go),
    golang: () => hljs.registerLanguage("go", go),
    javascript: () => hljs.registerLanguage("javascript", javascript),
    js: () => hljs.registerLanguage("javascript", javascript),
    typescript: () => hljs.registerLanguage("typescript", typescript),
    ts: () => hljs.registerLanguage("typescript", typescript),
    rust: () => hljs.registerLanguage("rust", rust),
    kotlin: () => hljs.registerLanguage("kotlin", kotlin),
    csharp: () => hljs.registerLanguage("csharp", csharp),
    cs: () => hljs.registerLanguage("csharp", csharp),
    ruby: () => hljs.registerLanguage("ruby", ruby),
    php: () => hljs.registerLanguage("php", php),
    scala: () => hljs.registerLanguage("scala", scala),
    cpp: () => hljs.registerLanguage("cpp", cpp),
    c: () => hljs.registerLanguage("cpp", cpp),
  };
  if (map[id]) {
    map[id]();
    registered.add(id);
    return id === "golang" ? "go" : id === "js" ? "javascript" : id === "ts" ? "typescript" : id === "cs" ? "csharp" : id;
  }
  if (id === "tsx") {
    hljs.registerLanguage("typescript", typescript);
    registered.add("tsx");
    return "typescript";
  }
  return "plaintext";
}

export function languageFromPath(path: string, fallback: string): string {
  const p = path.toLowerCase();
  if (p.endsWith(".py")) return "python";
  if (p.endsWith(".java")) return "java";
  if (p.endsWith(".go")) return "go";
  if (p.endsWith(".rs")) return "rust";
  if (p.endsWith(".kt") || p.endsWith(".kts")) return "kotlin";
  if (p.endsWith(".cs")) return "csharp";
  if (p.endsWith(".rb")) return "ruby";
  if (p.endsWith(".php")) return "php";
  if (p.endsWith(".scala")) return "scala";
  if (p.endsWith(".ts") || p.endsWith(".tsx")) return "typescript";
  if (p.endsWith(".js") || p.endsWith(".jsx") || p.endsWith(".mjs")) return "javascript";
  if (p.endsWith(".c") || p.endsWith(".h") || p.endsWith(".cpp") || p.endsWith(".hpp")) return "cpp";
  return ensureLanguage(fallback);
}

export function highlightLine(line: string, language: string): string {
  const lang = ensureLanguage(language);
  if (!line) {
    return " ";
  }
  const leading = line.match(/^(\s*)/)?.[1] ?? "";
  const rest = line.slice(leading.length);
  if (lang === "plaintext") {
    return escapeHtml(line);
  }
  if (!rest) {
    return escapeHtml(leading || " ");
  }
  try {
    return escapeHtml(leading) + hljs.highlight(rest, { language: lang, ignoreIllegals: true }).value;
  } catch {
    return escapeHtml(line);
  }
}

export function highlightBlock(code: string, language: string): string {
  const lang = ensureLanguage(language);
  if (!code.trim()) return "";
  try {
    return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
  } catch {
    return escapeHtml(code);
  }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

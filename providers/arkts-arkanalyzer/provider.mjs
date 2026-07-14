#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const PROVIDER_ID = "arkts-arkanalyzer";
const PROVIDER_VERSION = "0.1.0";
const MAX_ENTITIES = 50000;
const MAX_RELATIONS = 100000;

function call(value, name, fallback = undefined) {
  try {
    return value && typeof value[name] === "function" ? value[name]() : fallback;
  } catch {
    return fallback;
  }
}

function callWith(value, name, args, fallback = undefined) {
  try {
    return value && typeof value[name] === "function" ? value[name](...args) : fallback;
  } catch {
    return fallback;
  }
}

function values(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (value instanceof Map) return [...value.values()];
  if (typeof value[Symbol.iterator] === "function") return [...value];
  return [];
}

function text(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  try {
    const result = String(value);
    return result === "[object Object]" ? fallback : result;
  } catch {
    return fallback;
  }
}

function digest(value) {
  return createHash("sha256").update(value).digest("hex");
}

function symbolKey(language, filePath, qualifiedName, signature) {
  return `symbol:${digest(`${language}:${filePath}::${qualifiedName}|${signature}`).slice(0, 24)}`;
}

function safeRelative(root, candidate) {
  const relative = path.relative(root, path.resolve(candidate)).split(path.sep).join("/");
  if (!relative || relative.startsWith("../") || path.isAbsolute(relative)) return null;
  return relative;
}

function filePathOf(root, file) {
  const candidate = call(file, "getFilePath") ?? call(file, "getPath") ?? call(file, "getName");
  if (!candidate) return null;
  return safeRelative(root, path.isAbsolute(text(candidate)) ? text(candidate) : path.join(root, text(candidate)));
}

function positionOf(value) {
  const direct = call(value, "getLine") ?? call(value, "getLineNo");
  if (Number.isInteger(direct) && direct >= 1) return direct;
  const full = call(value, "getOriginFullPosition") ?? call(value, "getImplOriginFullPosition");
  const fullLine = call(full, "getFirstLine");
  if (Number.isInteger(fullLine) && fullLine >= 1) return fullLine;
  const position = call(value, "getLineColPosition") ?? call(value, "getOriginPositionInfo")
    ?? call(value, "getOriginPosition") ?? call(value, "getPosition");
  const line = call(position, "getLineNo") ?? call(position, "getLine") ?? position?.line;
  if (Number.isInteger(line) && line >= 0) return line === 0 ? 1 : line;
  const cfg = call(value, "getCfg");
  for (const stmt of values(call(cfg, "getStmts"))) {
    const stmtLine = positionOf(stmt);
    if (stmtLine) return stmtLine;
  }
  return 1;
}

function classKind(value) {
  const category = text(call(value, "getCategory")).toLowerCase();
  if (category.includes("interface")) return "interface";
  if (category.includes("struct") || category.includes("component")) return "component";
  return "class";
}

function exported(value) {
  const direct = call(value, "isExported");
  if (typeof direct === "boolean") return direct;
  const modifiers = text(call(value, "getModifiers")).toLowerCase();
  return modifiers.includes("export") || modifiers.includes("public");
}

function entity(language, filePath, name, kind, qualifiedName, signature, source) {
  const line = positionOf(source);
  return {
    key: symbolKey(language, filePath, qualifiedName, signature),
    file_path: filePath,
    name,
    kind,
    qualified_name: qualifiedName,
    signature,
    start_line: line,
    end_line: line,
    exported: exported(source),
    evidence_class: "exact",
  };
}

function signatureOf(value, fallback) {
  return text(call(value, "getSignature"), fallback) || fallback;
}

function qualifiedMethodName(owner, method) {
  return `${owner}.${text(call(method, "getName"), "anonymous")}`;
}

function relation(source, relationName, target, line, detail) {
  return {
    source_key: source.key,
    relation: relationName,
    target_key: target?.key ?? null,
    target_name: target?.name ?? null,
    target_qualified_name: target?.qualified_name ?? null,
    target_file_path: target?.file_path ?? null,
    line,
    confidence: 1.0,
    evidence_class: "exact",
    detail,
  };
}

function analyzerExports(module) {
  const api = module.default && typeof module.default === "object" ? { ...module.default, ...module } : module;
  if (typeof api.Scene !== "function" || typeof api.SceneConfig !== "function") {
    throw new Error("ArkAnalyzer Scene and SceneConfig exports are required");
  }
  return api;
}

async function buildScene(api, root) {
  const config = new api.SceneConfig();
  await Promise.resolve(config.buildFromProjectDir(root));
  const scene = new api.Scene();
  await Promise.resolve(scene.buildSceneFromProjectDir(config));
  await Promise.resolve(scene.inferTypes());
  return scene;
}

function collectModel(scene, request) {
  const requested = new Set(request.files.map((item) => item.path));
  const entities = [];
  const relations = [];
  const gaps = [];
  const byObject = new Map();
  const bySignature = new Map();
  const methods = [];
  for (const file of values(call(scene, "getFiles"))) {
    const filePath = filePathOf(request.project_root, file);
    if (!filePath || !requested.has(filePath)) continue;
    for (const arkClass of values(call(file, "getClasses"))) {
      const className = text(call(arkClass, "getName"), "anonymous");
      const classSignature = signatureOf(arkClass, `${classKind(arkClass)} ${className}`);
      const classEntity = entity(request.language, filePath, className, classKind(arkClass), className, classSignature, arkClass);
      entities.push(classEntity);
      byObject.set(arkClass, classEntity);
      bySignature.set(classSignature, classEntity);
      for (const method of values(call(arkClass, "getMethods"))) {
        const name = text(call(method, "getName"), "anonymous");
        const qualified = qualifiedMethodName(className, method);
        const signature = signatureOf(method, `${qualified}()`);
        const methodEntity = entity(request.language, filePath, name, "function", qualified, signature, method);
        entities.push(methodEntity);
        byObject.set(method, methodEntity);
        bySignature.set(signature, methodEntity);
        methods.push({ method, entity: methodEntity });
      }
      for (const field of values(call(arkClass, "getFields"))) {
        const name = text(call(field, "getName"), "anonymous");
        const qualified = `${className}.${name}`;
        const signature = signatureOf(field, qualified);
        const stateDecorators = values(call(field, "getStateDecorators"));
        const fieldEntity = entity(
          request.language, filePath, name, stateDecorators.length ? "state" : "field",
          qualified, signature, field,
        );
        entities.push(fieldEntity);
        byObject.set(field, fieldEntity);
        bySignature.set(signature, fieldEntity);
        if (stateDecorators.length) {
          relations.push(relation(classEntity, "owns_state", fieldEntity, positionOf(field), "ArkAnalyzer resolved ArkTS state decorator"));
        }
      }
    }
  }
  for (const { method, entity: source } of methods) {
    const cfg = call(method, "getCfg");
    for (const stmt of values(call(cfg, "getStmts"))) {
      const invoke = call(stmt, "getInvokeExpr");
      if (!invoke) continue;
      const targetSignature = text(call(invoke, "getMethodSignature"));
      const target = bySignature.get(targetSignature);
      if (target) relations.push(relation(source, "calls", target, positionOf(stmt), "ArkAnalyzer resolved invocation"));
      else if (targetSignature) gaps.push({ kind: "resolved_call_outside_requested_scope", path: source.file_path, detail: targetSignature.slice(0, 200) });
    }
    if (relations.length > MAX_RELATIONS) throw new Error(`semantic relation limit ${MAX_RELATIONS} exceeded`);
  }
  for (const [object, source] of byObject) {
    const parent = call(object, "getSuperClass");
    const target = byObject.get(parent);
    if (target) relations.push(relation(source, "extends", target, positionOf(object), "ArkAnalyzer resolved superclass"));
    const interfaceNames = values(call(object, "getImplementedInterfaceNames"));
    const implementedInterfaces = interfaceNames.length
      ? interfaceNames.map((name) => callWith(object, "getImplementedInterface", [name], null))
      : values(call(object, "getInterfaces"));
    for (let index = 0; index < implementedInterfaces.length; index += 1) {
      const implemented = interfaceNames.length
        ? implementedInterfaces[index]
        : implementedInterfaces[index];
      const interfaceTarget = byObject.get(implemented) ?? bySignature.get(text(implemented));
      if (interfaceTarget) relations.push(relation(source, "implements", interfaceTarget, positionOf(object), "ArkAnalyzer resolved interface"));
    }
  }
  if (entities.length > MAX_ENTITIES) throw new Error(`semantic entity limit ${MAX_ENTITIES} exceeded`);
  return { entities, relations, gaps: gaps.slice(0, 1000) };
}

async function validateSources(request) {
  const result = {};
  for (const item of request.files) {
    const source = await readFile(path.join(request.project_root, item.path), "utf8");
    const actual = digest(source);
    if (actual !== item.digest) throw new Error(`stale requested source: ${item.path}`);
    result[item.path] = actual;
  }
  return result;
}

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const request = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  if (request.schema_version !== "semantic-provider-request/v1" || request.language !== "ArkTS") {
    throw new Error("semantic-provider-request/v1 for ArkTS is required");
  }
  const moduleName = process.env.ARKANALYZER_MODULE || "arkanalyzer";
  let analyzer;
  try {
    analyzer = analyzerExports(await import(moduleName));
  } catch (error) {
    throw new Error(`ArkAnalyzer unavailable (${moduleName}); run pnpm install in provider directory: ${error.message}`);
  }
  const sourceDigests = await validateSources(request);
  const scene = await buildScene(analyzer, request.project_root);
  const model = collectModel(scene, request);
  const batch = {
    schema_version: "semantic-index/v1",
    adapter: { id: PROVIDER_ID, version: PROVIDER_VERSION, language: request.language },
    capabilities: ["definitions", "types", "calls", "inheritance", "state"],
    source_digests: sourceDigests,
    entities: model.entities,
    relations: model.relations,
    gaps: model.gaps,
  };
  process.stdout.write(JSON.stringify({
    schema_version: "semantic-provider-result/v1",
    request_id: request.request_id,
    provider: { id: PROVIDER_ID, version: PROVIDER_VERSION, toolchain: "ArkAnalyzer Scene/type inference" },
    batch,
  }));
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 2;
});

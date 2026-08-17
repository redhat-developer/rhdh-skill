#!/usr/bin/env node
/**
 * Bump Yarn across RHDH checkouts.
 *
 *   yarn set version <to>  → packageManager + yarnPath + binary
 *   chmod +x
 *   yarn install --mode=update-lockfile
 *   rewrite extras Yarn cannot see (ENV YARN= / Containerfile / embedded set version)
 *
 * No binary download. Bump GitHub workspaces first; copy yarn-<to>.cjs into
 * gitlab.cee.redhat.com midstream/distgit trees (rhidp/rhdh,
 * rhidp/rhdh-plugin-catalog) that only pin via ENV YARN= / checked-in releases.
 *
 *   bump-yarn.js --to 4.17.1 --root PATH... [--from V1,V2] [--dry-run] [--no-refresh-locks]
 *   bump-yarn.js --scan --root PATH
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const DEFAULT_FROM = ['4.12.0', '4.14.1'];
const SKIP = new Set(['.git', 'node_modules', '.yarn', 'dist', 'coverage', '.turbo']);
const YARN_BIN_RE = /^yarn-(\d{1,6}\.\d{1,6}\.\d{1,6})\.cjs$/;
const YARN_PM_RE = /^yarn@(\d{1,6}\.\d{1,6}\.\d{1,6})/;
const YARN_PATH_RE = /(?:^|\n)yarnPath:[^\n]*yarn-(\d{1,6}\.\d{1,6}\.\d{1,6})\.cjs/;

function cmpStr(a, b) {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

function parseArgs(argv) {
  const a = { from: [...DEFAULT_FROM], roots: [], to: null, scan: false, dryRun: false, locks: true };
  for (let i = 0; i < argv.length; i += 1) {
    const x = argv[i];
    if (x === '-h' || x === '--help') {
      console.log(`bump-yarn.js --to VER [--from ${DEFAULT_FROM}] --root PATH... [--scan|--dry-run|--no-refresh-locks]`);
      process.exit(0);
    }
    if (x === '--scan') a.scan = true;
    else if (x === '--dry-run') a.dryRun = true;
    else if (x === '--no-refresh-locks') a.locks = false;
    else if (x === '--to') a.to = argv[++i];
    else if (x === '--from') a.from = String(argv[++i]).split(',').map((s) => s.trim()).filter(Boolean);
    else if (x === '--root') a.roots.push(path.resolve(argv[++i]));
    else {
      console.error(`Unknown: ${x}`);
      process.exit(1);
    }
  }
  return a;
}

function pushWalkDir(stack, full, name) {
  if (!SKIP.has(name)) {
    stack.push(full);
    return;
  }
  if (name === '.yarn') {
    const releases = path.join(full, 'releases');
    if (fs.existsSync(releases)) stack.push(releases);
  }
}

function walkEntry(stack, dir, e, fn) {
  const full = path.join(dir, e.name);
  if (e.isDirectory()) {
    pushWalkDir(stack, full, e.name);
    return;
  }
  if (e.isFile()) fn(full, e.name, dir);
}

function walk(root, fn) {
  const stack = [root];
  while (stack.length) {
    const dir = stack.pop();
    let ents;
    try {
      ents = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of ents) walkEntry(stack, dir, e, fn);
  }
}

function esc(s) {
  return s.replaceAll(/[.*+?^${}()|[\]\\]/g, (ch) => `\\${ch}`);
}

function readPm(dir) {
  try {
    const pm = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')).packageManager || '';
    const m = YARN_PM_RE.exec(pm);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function readYarnPath(dir) {
  try {
    const m = YARN_PATH_RE.exec(fs.readFileSync(path.join(dir, '.yarnrc.yml'), 'utf8'));
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function localBin(dir) {
  try {
    const rel = path.join(dir, '.yarn', 'releases');
    const bins = fs.readdirSync(rel).filter((n) => YARN_BIN_RE.test(n)).toSorted(cmpStr);
    return bins.length ? path.join(rel, bins.at(-1)) : null;
  } catch {
    return null;
  }
}

/** Yarn CLI must be executable for yarnPath / node yarn-*.cjs. */
function chmodX(p) {
  try {
    fs.chmodSync(p, 0o755); // NOSONAR — intentional +x for Berry CLI binary
  } catch {
    /* ignore */
  }
}

function sh(cmd, args, cwd) {
  return spawnSync(cmd, args, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, YARN_ENABLE_IMMUTABLE_INSTALLS: 'false' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function setVersion(dir, to, dryRun) {
  if (dryRun) {
    console.log(`dry-run: set version ${to} @ ${dir}`);
    return;
  }
  console.log(`yarn set version: ${dir}`);
  const bin = localBin(dir);
  const r = bin
    ? sh(process.execPath, [bin, 'set', 'version', to], dir)
    : sh('yarn', ['set', 'version', to], dir);
  if (r.status) console.error(`warn: set version failed @ ${dir}`);
  const out = path.join(dir, '.yarn', 'releases', `yarn-${to}.cjs`);
  if (fs.existsSync(out)) chmodX(out);
}

function isExtra(full, base) {
  if (base === 'package.json' || base === '.yarnrc.yml') return false;
  if (base === 'Containerfile' || base === 'Dockerfile' || base === 'run-e2e.sh') return true;
  if (base.endsWith('.Containerfile') || base.endsWith('.Dockerfile')) return true;
  if (base === 'yarn' && full.includes(`${path.sep}.fullsend${path.sep}`) && full.endsWith(`${path.sep}bin${path.sep}yarn`)) {
    return true;
  }
  return base.endsWith('.sh') && /e2e|yarn/i.test(full);
}

function rewriteExtras(text, from, to) {
  const alt = from.map(esc).join('|');
  return text
    .replace(new RegExp(String.raw`yarn-(?:${alt})\.cjs`, 'g'), `yarn-${to}.cjs`)
    .replace(new RegExp(String.raw`yarn set version (?:${alt})\b`, 'g'), `yarn set version ${to}`);
}

function resolveToBin(dir, to) {
  for (let cur = dir, i = 0; i < 8; i += 1) {
    const c = path.join(cur, '.yarn', 'releases', `yarn-${to}.cjs`);
    if (fs.existsSync(c)) return c;
    const parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return null;
}

function bumpCount(map, key) {
  map.set(key, (map.get(key) || 0) + 1);
}

function fmtCounts(map) {
  return [...map.entries()].toSorted(([a], [b]) => cmpStr(a, b)).map(([v, n]) => `${v}×${n}`).join(', ') || '(none)';
}

function scan(root) {
  const releases = new Map();
  const pms = new Map();
  walk(root, (_full, base, dir) => {
    const m = YARN_BIN_RE.exec(base);
    if (m) {
      bumpCount(releases, m[1]);
      return;
    }
    if (base !== 'package.json') return;
    const v = readPm(dir);
    if (v) bumpCount(pms, v);
  });
  console.log(`\n=== scan ${root} ===\nreleases: ${fmtCounts(releases)}\npackageManager: ${fmtCounts(pms)}`);
}

function collectPmDirs(root, fromSet) {
  const pmDirs = [];
  walk(root, (_f, base, dir) => {
    if (base === 'package.json' && fromSet.has(readPm(dir))) pmDirs.push(dir);
  });
  return pmDirs.toSorted(cmpStr);
}

function applyExtras(root, from, to, dryRun) {
  const extras = [];
  walk(root, (full, base) => {
    if (!isExtra(full, base)) return;
    let text;
    try {
      text = fs.readFileSync(full, 'utf8');
    } catch {
      return;
    }
    if (text.length > 2e6) return;
    const next = rewriteExtras(text, from, to);
    if (next === text) return;
    const rel = path.relative(root, full);
    extras.push(rel);
    if (dryRun) console.log(`dry-run: extra ${rel}`);
    else fs.writeFileSync(full, next);
  });
  return extras;
}

function shouldSkipLock(full) {
  return full.split(path.sep).some((p) => p === 'node_modules' || p === 'dist-dynamic');
}

function dropUntrackedYarnrc(dir, root) {
  const rc = path.join(dir, '.yarnrc.yml');
  if (!fs.existsSync(rc)) return;
  if (sh('git', ['ls-files', '--error-unmatch', rc], root).status === 0) return;
  try {
    fs.unlinkSync(rc);
  } catch {
    /* ignore */
  }
}

function refreshOneLock(dir, to, root) {
  const bin = resolveToBin(dir, to);
  if (!bin) {
    console.error(
      `warn: no yarn-${to}.cjs for ${dir} (bump a GH workspace first, or copy the binary into .yarn/releases/)`,
    );
    return 'fail';
  }
  console.log(`locks: ${dir}`);
  const failed = Boolean(sh(process.execPath, [bin, 'install', '--mode=update-lockfile'], dir).status);
  if (failed) console.error(`warn: install failed @ ${dir}`);
  dropUntrackedYarnrc(dir, root);
  return failed ? 'fail' : 'ok';
}

function refreshLocks(root, { fromSet, to }) {
  const stats = { ok: 0, skip: 0, fail: 0 };
  const dirs = [];
  walk(root, (full, base, dir) => {
    if (base !== 'yarn.lock' || shouldSkipLock(full)) return;
    const pin = readPm(dir) || readYarnPath(dir);
    if (pin && pin !== to && !fromSet.has(pin)) {
      stats.skip += 1;
      console.log(`locks: skip ${dir} (${pin})`);
      return;
    }
    dirs.push(dir);
  });
  for (const dir of dirs.toSorted(cmpStr)) {
    stats[refreshOneLock(dir, to, root)] += 1;
  }
  return stats;
}

function bump(root, { from, to, dryRun, locks }) {
  const fromSet = new Set(from);
  const pmDirs = collectPmDirs(root, fromSet);
  for (const d of pmDirs) setVersion(d, to, dryRun);

  const extras = applyExtras(root, from, to, dryRun);
  const lockStats = locks && !dryRun ? refreshLocks(root, { fromSet, to }) : null;

  let summary = `\n=== ${root} ===\nset-version: ${pmDirs.length}  extras: ${extras.length}`;
  if (extras.length) summary += `\n  ${extras.join('\n  ')}`;
  if (lockStats) summary += `\nlocks ok/skip/fail: ${lockStats.ok}/${lockStats.skip}/${lockStats.fail}`;
  console.log(summary);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.roots.length) {
    console.error('Need --root PATH');
    process.exit(1);
  }
  for (const r of args.roots) {
    if (!fs.existsSync(r)) {
      console.error(`Missing: ${r}`);
      process.exit(1);
    }
  }
  if (args.scan) {
    for (const r of args.roots) scan(r);
    return;
  }
  if (!args.to) {
    console.error('--to VERSION required (exact, not stable)');
    process.exit(1);
  }
  console.log(`to=${args.to} from=${args.from.join(',')} dry-run=${args.dryRun} locks=${args.locks}`);
  for (const r of args.roots) bump(r, args);
}

main();

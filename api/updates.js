import { createHash } from 'node:crypto';

const REPO = 'gba45684-lab/RESUMATE-CLAUDE-';
const BUNDLE = 'resumate-bundle.zip';

// Latest release from the GitHub API (fast; needs GITHUB_TOKEN to avoid the 60-per-hour limit).
async function latestFromApi() {
  const headers = { 'Accept': 'application/vnd.github+json', 'User-Agent': 'ResuMate-OTA' };
  if (process.env.GITHUB_TOKEN) headers.Authorization = 'Bearer ' + process.env.GITHUB_TOKEN;
  const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers }).catch(() => null);
  if (!r || !r.ok) {
    console.error('update check: GitHub API failed with status', r ? r.status : 'network', 'token set:', !!process.env.GITHUB_TOKEN);
    return null;
  }
  const rel = await r.json();
  const asset = (rel.assets || []).find(a => a.name === BUNDLE);
  if (!rel.tag_name || !asset) return null;
  return {
    tag: String(rel.tag_name),
    url: asset.browser_download_url,
    checksum: String(asset.digest || '').replace(/^sha256:/, '') || null
  };
}

// Fallback without the API and without a token: GitHub's public release page redirects to the newest tag.
async function latestFromPage() {
  const r = await fetch(`https://github.com/${REPO}/releases/latest`, { redirect: 'manual' }).catch(() => null);
  const loc = (r && r.headers.get('location')) || '';
  const m = loc.match(/\/releases\/tag\/([^/?#]+)$/);
  if (!m) { console.error('update check: release page gave no tag'); return null; }
  const tag = decodeURIComponent(m[1]);
  return { tag, url: `https://github.com/${REPO}/releases/download/${tag}/${BUNDLE}`, checksum: null };
}

async function sha256Of(url) {
  const r = await fetch(url).catch(() => null);
  if (!r || !r.ok) return null;
  return createHash('sha256').update(Buffer.from(await r.arrayBuffer())).digest('hex');
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  // cache for 1 minute so a new release reaches phones quickly
  res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=30');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ message: 'Method not allowed' });

  try {
    const info = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    if (info.app_id && info.app_id !== 'com.resumate.claude') {
      return res.status(200).json({ message: 'No update for this app', version: info.version_name || '' });
    }
    const current = String(info.version_name || '0.0.0').replace(/^v/, '');

    const rel = (await latestFromApi()) || (await latestFromPage());
    if (!rel) return res.status(200).json({ message: 'No update available', version: current });

    const version = rel.tag.replace(/^v/, '');
    const parts = s => s.split('.').map(x => parseInt(x, 10) || 0);
    const a = parts(version), b = parts(current);
    const newer = a[0] > b[0] || (a[0] === b[0] && (a[1] > b[1] || (a[1] === b[1] && a[2] > b[2])));
    if (!version || !newer) return res.status(200).json({ message: 'Already up to date', version: current });

    const checksum = rel.checksum || (await sha256Of(rel.url));
    if (!checksum) return res.status(200).json({ message: 'Update checksum unavailable', version: current });

    return res.status(200).json({ version, url: rel.url, checksum });
  } catch (error) {
    console.error('update check failed', error && error.message);
    return res.status(200).json({ message: 'Update check failed safely' });
  }
}

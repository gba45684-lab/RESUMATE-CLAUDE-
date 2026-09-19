export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ message: 'Method not allowed' });

  try {
    const info = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    if (info.app_id && info.app_id !== 'com.krapal.resumeforge') {
      return res.status(200).json({ message: 'No update for this app', version: info.version_name || '' });
    }

    const gh = await fetch('https://api.github.com/repos/gba45684-lab/RESUMATE-CLAUDE-/releases/latest', {
      headers: { 'Accept': 'application/vnd.github+json', 'User-Agent': 'ResuMate-OTA' }
    });
    if (!gh.ok) return res.status(200).json({ message: 'No update available', version: info.version_name || '' });

    const release = await gh.json();
    const version = String(release.tag_name || '').replace(/^v/, '');
    const current = String(info.version_name || '0.0.0').replace(/^v/, '');

    const parts = s => s.split('.').map(x => parseInt(x, 10) || 0);
    const a = parts(version), b = parts(current);
    const newer = a[0] > b[0] || (a[0] === b[0] && (a[1] > b[1] || (a[1] === b[1] && a[2] > b[2])));
    if (!version || !newer) return res.status(200).json({ message: 'Already up to date', version: current });

    const asset = (release.assets || []).find(x => x.name === 'resumate-bundle.zip');
    if (!asset) return res.status(200).json({ message: 'Update bundle unavailable', version: current });

    const digest = String(asset.digest || '').replace(/^sha256:/, '');
    if (!digest) return res.status(200).json({ message: 'Update checksum unavailable', version: current });

    return res.status(200).json({
      version,
      url: asset.browser_download_url,
      checksum: digest
    });
  } catch (error) {
    return res.status(200).json({ message: 'Update check failed safely' });
  }
}

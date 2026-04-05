// js/github.js
import { GITHUB_REPO } from './config.js';

export async function triggerScraper() {
  const pat = localStorage.getItem('github_pat');
  if (!pat) return false;

  const res = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/scraper.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${pat}`,
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({ ref: 'main' }),
    },
  );
  return res.status === 204;
}

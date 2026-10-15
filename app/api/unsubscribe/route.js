import { NextResponse } from 'next/server';

const REPO = process.env.GITHUB_REPO || 'anonymous99-Rise/ai-daily-newsletter';
const API = `https://api.github.com/repos/${REPO}`;

function githubHeaders(token) {
  return {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/json',
  };
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function successPage(message) {
  return new NextResponse(
    `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Daily Newsletter</title></head>
<body style="margin:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;">
<div style="background:#fff;border-radius:16px;padding:40px 32px;max-width:420px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
<div style="font-size:40px;margin-bottom:12px;">&#128279;</div>
<h2 style="font-size:20px;font-weight:700;color:#1e293b;margin:0 0 8px;">${message}</h2>
<p style="color:#64748b;font-size:14px;margin:0;">AI Daily Newsletter</p>
</div></body></html>`,
    { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } }
  );
}

async function removeSubscriber(token, email) {
  const getRes = await fetch(`${API}/contents/data/subscribers.json`, {
    headers: githubHeaders(token),
    cache: 'no-store',
  });
  if (getRes.status === 404) return { ok: true, removed: false };
  if (!getRes.ok) throw new Error(`GitHub API 读取失败: ${getRes.status}`);
  const file = await getRes.json();
  const subscribers = JSON.parse(Buffer.from(file.content, 'base64').toString('utf-8'));
  if (!subscribers[email]) return { ok: true, removed: false };
  delete subscribers[email];
  const putRes = await fetch(`${API}/contents/data/subscribers.json`, {
    method: 'PUT',
    headers: githubHeaders(token),
    body: JSON.stringify({
      message: `chore: unsubscribe ${email} [skip ci]`,
      content: Buffer.from(JSON.stringify(subscribers, null, 2)).toString('base64'),
      sha: file.sha,
    }),
  });
  if (!putRes.ok) throw new Error(`GitHub API 写入失败: ${putRes.status}`);
  return { ok: true, removed: true };
}

async function handleUnsubscribe(request) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    console.error('Unsubscribe error: GITHUB_TOKEN 环境变量未配置');
    return NextResponse.json({ error: '服务未配置' }, { status: 500 });
  }

  let email;
  if (request.method === 'GET') {
    email = new URL(request.url).searchParams.get('email');
  } else {
    ({ email } = await request.json());
  }
  if (!email || !isValidEmail(email))
    return NextResponse.json({ error: '请提供有效的邮箱地址' }, { status: 400 });

  try {
    await removeSubscriber(token, email);
    if (request.method === 'GET') return successPage('已取消订阅');
    return NextResponse.json({ message: '已取消订阅' });
  } catch (error) {
    console.error('Unsubscribe error:', error);
    if (request.method === 'GET') return successPage('操作失败，请稍后重试');
    return NextResponse.json({ error: '操作失败' }, { status: 500 });
  }
}

export async function GET(request) { return handleUnsubscribe(request); }
export async function POST(request) { return handleUnsubscribe(request); }

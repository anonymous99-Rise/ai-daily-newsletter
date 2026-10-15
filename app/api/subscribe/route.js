import { NextResponse } from 'next/server';

// 环境变量：GITHUB_TOKEN（fine-grained PAT，Contents 读写 + Actions 写权限）
// 建议同时配置 GITHUB_REPO，默认 anonymous99-Rise/ai-daily-newsletter
const REPO = process.env.GITHUB_REPO || 'anonymous99-Rise/ai-daily-newsletter';
const API = `https://api.github.com/repos/${REPO}`;

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function githubHeaders(token) {
  return {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/json',
  };
}

async function getSubscribers(token) {
  const res = await fetch(`${API}/contents/data/subscribers.json`, {
    headers: githubHeaders(token),
    cache: 'no-store',
  });
  if (res.status === 404) return {};
  if (!res.ok) throw new Error(`GitHub API 读取失败: ${res.status}`);
  const file = await res.json();
  return JSON.parse(Buffer.from(file.content, 'base64').toString('utf-8'));
}

export async function POST(request) {
  try {
    const token = process.env.GITHUB_TOKEN;
    if (!token) {
      console.error('Subscribe error: GITHUB_TOKEN 环境变量未配置');
      return NextResponse.json({ error: '服务未配置，请联系管理员' }, { status: 500 });
    }

    const { email } = await request.json();
    if (!email || !isValidEmail(email))
      return NextResponse.json({ error: '请提供有效的邮箱地址' }, { status: 400 });

    const subscribers = await getSubscribers(token);
    if (subscribers[email])
      return NextResponse.json({ error: '该邮箱已订阅' }, { status: 409 });

    // 无状态确认 token：email|timestamp|hmac
    const secret = process.env.CONFIRM_SECRET;
    if (!secret) {
      console.error('Subscribe error: CONFIRM_SECRET 环境变量未配置');
      return NextResponse.json({ error: '服务未配置，请联系管理员' }, { status: 500 });
    }
    const crypto = await import('crypto');
    const ts = Date.now().toString();
    const sig = crypto.createHmac('sha256', secret).update(`${email}|${ts}`).digest('base64url');
    const confirmToken = `${Buffer.from(email).toString('base64url')}.${ts}.${sig}`;

    const origin = new URL(request.url).origin;
    const res = await fetch(`${API}/dispatches`, {
      method: 'POST',
      headers: githubHeaders(token),
      body: JSON.stringify({
        event_type: 'confirm-subscription',
        client_payload: { email, token: confirmToken, origin },
      }),
    });
    if (!res.ok) {
      console.error('GitHub dispatch error:', res.status, await res.text());
      return NextResponse.json({ error: '订阅失败，请稍后重试' }, { status: 500 });
    }

    return NextResponse.json({ message: '已发送确认邮件，请查收并点击确认链接完成订阅' });
  } catch (error) {
    console.error('Subscribe error:', error);
    return NextResponse.json({ error: '订阅失败，请稍后重试' }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({ usage: 'POST /api/subscribe with { "email": "your@email.com" }' });
}

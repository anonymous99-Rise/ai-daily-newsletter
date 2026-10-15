import { NextResponse } from 'next/server';
import crypto from 'crypto';

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

function verifyToken(token) {
  try {
    const secret = process.env.CONFIRM_SECRET;
    if (!secret) return null;
    const [emailB64, ts, sig] = token.split('.');
    if (!emailB64 || !ts || !sig) return null;
    const email = Buffer.from(emailB64, 'base64url').toString('utf-8');
    const expected = crypto.createHmac('sha256', secret).update(`${email}|${ts}`).digest('base64url');
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
    if (Date.now() - Number(ts) > 24 * 60 * 60 * 1000) return null;
    return email;
  } catch { return null; }
}

export async function GET(request) {
  const token = process.env.GITHUB_TOKEN;
  const origin = new URL(request.url).origin;

  if (!token) {
    console.error('Confirm error: GITHUB_TOKEN 环境变量未配置');
    return NextResponse.redirect(`${origin}/?subscribe_error=unconfigured`);
  }

  const confirmToken = new URL(request.url).searchParams.get('token');
  const email = confirmToken && verifyToken(confirmToken);
  if (!email) return NextResponse.redirect(`${origin}/?subscribe_error=invalid`);

  try {
    // 读取现有订阅者（带 sha 用于更新）
    const getRes = await fetch(`${API}/contents/data/subscribers.json`, {
      headers: githubHeaders(token),
      cache: 'no-store',
    });
    let subscribers = {};
    let sha = undefined;
    if (getRes.ok) {
      const file = await getRes.json();
      sha = file.sha;
      subscribers = JSON.parse(Buffer.from(file.content, 'base64').toString('utf-8'));
    } else if (getRes.status !== 404) {
      throw new Error(`GitHub API 读取失败: ${getRes.status}`);
    }

    if (!subscribers[email]) {
      subscribers[email] = { subscribedAt: new Date().toISOString(), confirmed: true };
      const putRes = await fetch(`${API}/contents/data/subscribers.json`, {
        method: 'PUT',
        headers: githubHeaders(token),
        body: JSON.stringify({
          message: `chore: confirm subscription for ${email} [skip ci]`,
          content: Buffer.from(JSON.stringify(subscribers, null, 2)).toString('base64'),
          ...(sha ? { sha } : {}),
        }),
      });
      if (!putRes.ok) throw new Error(`GitHub API 写入失败: ${putRes.status} ${await putRes.text()}`);
    }

    return NextResponse.redirect(`${origin}/?subscribed=true`);
  } catch (error) {
    console.error('Confirm error:', error);
    return NextResponse.redirect(`${origin}/?subscribe_error=server`);
  }
}

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase = SUPABASE_URL && SUPABASE_KEY ? createClient(SUPABASE_URL, SUPABASE_KEY) : null;

export async function POST(req) {
  try {
    const body = await req.json();
    const { session_id, page, user_agent, events } = body || {};

    if (!events || !Array.isArray(events) || events.length === 0) {
      return new Response(JSON.stringify({ error: 'No events provided' }), { status: 400 });
    }

    if (!supabase) {
      return new Response(JSON.stringify({ error: 'Supabase not configured on server' }), { status: 500 });
    }

    const payload = {
      session_id: session_id || null,
      page: page || null,
      user_agent: user_agent || null,
      events,
    };

    const { data, error } = await supabase.from('captcha_event_batches').insert(payload).select();

    if (error) {
      console.error('Supabase insert error', error);
      return new Response(JSON.stringify({ error: error.message }), { status: 500 });
    }

    return new Response(JSON.stringify({ ok: true, inserted: data }), { status: 200 });
  } catch (err) {
    console.error(err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}

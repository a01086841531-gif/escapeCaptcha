import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Create a lazy-initialized Supabase client
// Only actually create the client when valid URLs are provided
let _supabase = null;

export function getSupabase() {
  if (_supabase) return _supabase;

  if (!supabaseUrl || !supabaseUrl.startsWith('http')) {
    // Return a mock client for development without Supabase configured
    return {
      auth: {
        signInWithPassword: async () => ({
          data: null,
          error: { message: 'Supabase가 설정되지 않았습니다. .env.local 파일을 확인해주세요.' },
        }),
        signUp: async () => ({
          data: null,
          error: { message: 'Supabase가 설정되지 않았습니다. .env.local 파일을 확인해주세요.' },
        }),
      },
    };
  }

  _supabase = createClient(supabaseUrl, supabaseAnonKey);
  return _supabase;
}

// For backward compatibility
export const supabase = typeof window !== 'undefined' ? getSupabase() : null;

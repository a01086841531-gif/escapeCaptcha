import { spawn } from 'child_process';
import path from 'path';

const SCRIPT_PATH = path.join(process.cwd(), 'ai', 'score_model.py');

function getPythonCandidates() {
  const explicit = process.env.PYTHON || process.env.PYTHON_PATH;
  if (explicit) {
    return [{ command: explicit, args: [SCRIPT_PATH] }];
  }

  if (process.platform === 'win32') {
    return [
      { command: 'python', args: [SCRIPT_PATH] },
      { command: 'py', args: ['-3', SCRIPT_PATH] },
      { command: 'python3', args: [SCRIPT_PATH] },
    ];
  }

  return [
    { command: 'python3', args: [SCRIPT_PATH] },
    { command: 'python', args: [SCRIPT_PATH] },
  ];
}

async function runPythonScript(events) {
  const candidates = getPythonCandidates();
  const errors = [];

  for (const candidate of candidates) {
    const child = spawn(candidate.command, candidate.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    const stdoutChunks = [];
    const stderrChunks = [];

    child.stdout.on('data', (chunk) => stdoutChunks.push(chunk));
    child.stderr.on('data', (chunk) => stderrChunks.push(chunk));

    const exitCode = await new Promise((resolve, reject) => {
      child.on('error', reject);
      child.on('close', resolve);
      child.stdin.write(JSON.stringify({ events }));
      child.stdin.end();
    }).catch((err) => {
      errors.push({ command: candidate.command, error: err.message });
      return null;
    });

    const stdout = Buffer.concat(stdoutChunks).toString('utf8').trim();
    const stderr = Buffer.concat(stderrChunks).toString('utf8').trim();

    if (exitCode === 0) {
      return { stdout, stderr, command: candidate.command };
    }

    errors.push({ command: candidate.command, exitCode, stderr: stderr || stdout });
  }

  throw new Error(
    `Unable to run Python model scoring. Tried: ${errors
      .map((entry) => `${entry.command} (${entry.exitCode || 'ERR'}): ${entry.error || entry.stderr}`)
      .join(' | ')}`
  );
}

export async function POST(req) {
  try {
    const body = await req.json();
    const { events } = body || {};

    if (!events || !Array.isArray(events) || events.length === 0) {
      return new Response(JSON.stringify({ error: 'Event batch required' }), { status: 400 });
    }

    const { stdout, stderr, command } = await runPythonScript(events);

    if (stderr) {
      console.warn(`Python scoring process (${command}) stderr:`, stderr);
    }

    let result;
    try {
      result = JSON.parse(stdout);
    } catch (err) {
      console.error('Failed to parse score output:', stdout, err);
      return new Response(JSON.stringify({ error: 'Invalid model scoring response' }), { status: 500 });
    }

    if (result.error) {
      return new Response(JSON.stringify({ error: result.error }), { status: 500 });
    }

    return new Response(JSON.stringify(result), { status: 200 });
  } catch (err) {
    console.error('Captcha score API error:', err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}

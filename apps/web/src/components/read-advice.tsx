'use client';

import {useEffect, useRef, useState} from 'react';
import {Square, Volume2} from 'lucide-react';
import {farmerGuidancePhrases} from '../lib/farmer-guidance';
import type {Locale} from '../lib/messages';

type Props = {text: string; locale: Locale};
type PlaybackState = 'idle' | 'playing' | 'error';
type Clip = {text: string; src: string};

function clipFor(text: string, locale: Locale): Clip {
  // Content-based filenames also invalidate recordings when the guidance changes.
  let hash = 2166136261;
  for (const character of text) hash = Math.imul(hash ^ character.codePointAt(0)!, 16777619);
  const name = (hash >>> 0).toString(16).padStart(8, '0');
  return {text, src: '/advice-audio/' + locale + '/' + name + '.mp3'};
}

const recordings = {
  bn: farmerGuidancePhrases.map(phrase => clipFor(phrase.bn, 'bn')),
  en: farmerGuidancePhrases.map(phrase => clipFor(phrase.en, 'en')),
};

export function adviceClips(text: string, locale: Locale): Clip[] | null {
  const clips: Clip[] = [];
  let remaining = text.trim();
  while (remaining) {
    const next = recordings[locale].find(clip =>
      remaining === clip.text || remaining.startsWith(clip.text + ' '));
    if (!next) return null;
    clips.push(next);
    remaining = remaining.slice(next.text.length).trimStart();
  }
  return clips.length ? clips : null;
}

export function playAdvice(
  text: string, locale: Locale, onFinish: (state: 'idle' | 'error') => void, recordingsOnly = false,
) {
  const clips = adviceClips(text, locale);
  const speech = window.speechSynthesis;
  const language = locale === 'bn' ? 'bn-BD' : 'en-US';
  const voices = recordingsOnly ? [] : (speech?.getVoices() ?? []).filter(voice =>
    voice.localService && voice.lang.toLowerCase().replaceAll('_', '-').split('-')[0] === locale);
  const voice = voices.find(item => item.lang.toLowerCase().replaceAll('_', '-') === language.toLowerCase()) ?? voices[0];
  let at = 0;
  let stopped = false;
  let utterance: SpeechSynthesisUtterance | null = null;
  let audio: HTMLAudioElement | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;

  function releaseSpeech(cancel: boolean) {
    clearTimeout(timeout);
    if (utterance) {
      utterance.onstart = utterance.onend = utterance.onerror = null;
      utterance = null;
      if (cancel) speech.cancel();
    }
  }

  function stop() {
    if (stopped) return;
    stopped = true;
    releaseSpeech(true);
    if (audio) {
      audio.onerror = audio.onended = null;
      audio.pause();
    }
  }

  function finish(state: 'idle' | 'error') {
    if (stopped) return;
    stop();
    onFinish(state);
  }

  function playRecording() {
    if (stopped) return;
    releaseSpeech(true);
    if (!clips || typeof Audio === 'undefined') { finish('error'); return; }
    if (at === clips.length) { finish('idle'); return; }
    // Reuse the element that received the user gesture across the whole playlist.
    audio ??= new Audio();
    audio.onended = () => { at++; playRecording(); };
    audio.onerror = () => finish('error');
    audio.src = clips[at].src;
    try { void audio.play().catch(() => finish('error')); }
    catch { finish('error'); }
  }

  function speakPhrase() {
    if (stopped) return;
    if (!voice || typeof SpeechSynthesisUtterance === 'undefined') { playRecording(); return; }
    const next = clips ? clips[at]?.text : at === 0 ? text : undefined;
    if (!next) { finish('idle'); return; }
    utterance = new SpeechSynthesisUtterance(next);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 0.95;
    utterance.onstart = () => {
      clearTimeout(timeout);
      // Some platform engines stop delivering callbacks midway through an utterance.
      timeout = setTimeout(playRecording, Math.max(20000, next.length * 150));
    };
    utterance.onend = () => { releaseSpeech(false); at++; speakPhrase(); };
    utterance.onerror = playRecording;
    timeout = setTimeout(playRecording, 2500);
    try { speech.speak(utterance); }
    catch { playRecording(); }
  }

  speakPhrase();
  return stop;
}

function ReaderControl({text, locale}: Props) {
  const [state, setState] = useState<PlaybackState>('idle');
  const cancel = useRef<(() => void) | undefined>(undefined);
  useEffect(() => () => cancel.current?.(), []);
  const active = state === 'playing';
  const label = locale === 'bn' ? (active ? 'থামান' : 'শুনুন') : (active ? 'Stop' : 'Listen');

  function toggle() {
    if (active) {
      cancel.current?.();
      setState('idle');
    } else {
      setState('playing');
      // A fresh tap lets mobile browsers start the recording after a playback denial.
      cancel.current = playAdvice(text, locale, setState, state === 'error');
    }
  }

  return <div>
    <button type="button" className="btn secondary" lang={locale} onClick={toggle}
      disabled={!text.trim()} aria-pressed={active}>
      {active ? <Square size={17} aria-hidden="true"/> : <Volume2 size={17} aria-hidden="true"/>}
      {label}
    </button>
    {state === 'error' && <p role="status">{locale === 'bn'
      ? 'শব্দ চালানো যায়নি। আবার শুনতে চাপুন।'
      : 'Audio could not play. Tap Listen to try again.'}</p>}
  </div>;
}

export function ReadAdvice({text, locale}: Props) {
  return <ReaderControl key={locale + text} text={text} locale={locale}/>;
}

import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {adviceClips, playAdvice} from '../src/components/read-advice';
import {farmerGuidancePhrases} from '../src/lib/farmer-guidance';

const [first, second] = farmerGuidancePhrases;

function browser(voices: Partial<SpeechSynthesisVoice>[] = []) {
  class Utterance {
    constructor(public text: string) {}
    lang = '';
    voice: SpeechSynthesisVoice | null = null;
    onstart: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onend: (() => void) | null = null;
  }
  const speech = {getVoices: () => voices, speak: vi.fn<(u: Utterance) => void>(), cancel: vi.fn()};
  const audio = {
    src: '', onended: null as (() => void) | null, onerror: null as (() => void) | null,
    play: vi.fn().mockResolvedValue(undefined), pause: vi.fn(),
  };
  vi.stubGlobal('window', {speechSynthesis: speech});
  vi.stubGlobal('SpeechSynthesisUtterance', Utterance);
  vi.stubGlobal('Audio', class {constructor() {return audio;}});
  return {audio, speech};
}

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('spoken farmer guidance', () => {
  it.each(['bn','en'] as const)('ships an MP3 for each exact %s phrase, in playback order', locale => {
    const all = farmerGuidancePhrases.map(p => p[locale]);
    const clips = adviceClips(all.join(' '), locale)!;
    expect(clips).toHaveLength(all.length);
    expect(new Set(clips.map(c => c.src)).size).toBe(all.length);
    expect(clips.map(c => c.text)).toEqual(all);
    for (const {src} of clips) {
      expect(src).toMatch(new RegExp('^/advice-audio/' + locale + '/[a-f0-9]{8}\\.mp3$'));
      const bytes = readFileSync(resolve('public', src.slice(1)));
      expect(bytes.subarray(0,3).toString()).toBe('ID3');
      expect(bytes.length).toBeGreaterThan(3500);
    }
    expect(adviceClips(all[0] + ' unknown', locale)).toBeNull();
  });

  it('reads in the exact local Bangladeshi voice when available', () => {
    const voices = [{lang:'bn-IN',localService:true}, {lang:'bn-BD',localService:true}];
    const {speech, audio} = browser(voices);
    const finished = vi.fn();
    playAdvice(first.bn, 'bn', finished);
    const utterance = speech.speak.mock.calls[0][0];
    expect([utterance.text, utterance.lang, utterance.voice]).toEqual([first.bn, 'bn-BD', voices[1]]);
    utterance.onend!();
    expect(finished).toHaveBeenCalledWith('idle');
    expect(audio.play).not.toHaveBeenCalled();
  });

  it('uses bundled clips in order when only other languages or remote voices are installed', () => {
    const {speech, audio} = browser([{lang:'en-US',localService:true}, {lang:'bn-BD',localService:false}]);
    const finished = vi.fn();
    const text = [first.bn, second.bn].join(' ');
    const clips = adviceClips(text, 'bn')!;
    playAdvice(text, 'bn', finished);
    expect(audio.src).toBe(clips[0].src);
    audio.onended!();
    expect(audio.src).toBe(clips[1].src);
    audio.onended!();
    expect(speech.speak).not.toHaveBeenCalled();
    expect(finished).toHaveBeenCalledWith('idle');
  });

  it('continues from the failing phrase if native synthesis breaks halfway', () => {
    const {speech,audio} = browser([{lang:'en-GB',localService:true}]);
    const text = [first.en, second.en].join(' ');
    const stop = playAdvice(text, 'en', vi.fn());
    speech.speak.mock.calls[0][0].onend!();
    speech.speak.mock.calls[1][0].onerror!();
    expect(audio.src).toBe(adviceClips(second.en, 'en')![0].src);
    stop();
    expect(audio.pause).toHaveBeenCalledOnce();
    expect(audio.onended).toBeNull();
  });

  it('recovers from a device voice that never starts and cancels cleanly', () => {
    vi.useFakeTimers();
    const {speech,audio} = browser([{lang:'bn-IN',localService:true}]);
    const finished = vi.fn();
    const stop = playAdvice(first.bn, 'bn', finished);
    vi.advanceTimersByTime(4000);
    expect(speech.cancel).toHaveBeenCalledOnce();
    expect(audio.play).toHaveBeenCalledOnce();
    stop();
    expect(audio.pause).toHaveBeenCalledOnce();
    expect(finished).not.toHaveBeenCalled();
  });

  it('reports a playback failure and ignores late failures after stop', async () => {
    const {audio} = browser();
    audio.play.mockRejectedValue(new Error('Audio blocked'));
    const finished = vi.fn();
    playAdvice(first.bn, 'bn', finished);
    await Promise.resolve();
    expect(finished).toHaveBeenCalledWith('error');
    finished.mockClear();
    const stop = playAdvice(first.bn, 'bn', finished);
    stop();
    await Promise.resolve();
    expect(finished).not.toHaveBeenCalled();
  });
});

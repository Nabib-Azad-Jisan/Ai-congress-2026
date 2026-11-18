'use client';

import Link from 'next/link';
import {useRef, useState, type FormEvent} from 'react';
import {useQuery} from '@tanstack/react-query';
import {ArrowRight, Leaf, ShieldCheck} from 'lucide-react';
import {request, setSessionToken} from '@/lib/api';

type Locale = 'en' | 'bn';
type Role = 'farmer' | 'customer' | 'admin';
type Purpose = 'login' | 'signup';

type SignupProfile = {
  name: string;
  age: number;
  role: 'farmer' | 'customer';
  national_id: string;
  permanent_address: string;
  present_address: string;
  ward_number: string;
  gender: string;
  photo_base64: string;
  password: string;
  confirm_password: string;
};

function photoBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
    reader.onerror = () => reject(new Error('Could not read the photo.'));
    reader.readAsDataURL(file);
  });
}

export function AccountAccess({locale, marketplace = false}: {locale: Locale; marketplace?: boolean}) {
  const t = (en: string, bn: string) => locale === 'bn' ? bn : en;
  const [purpose, setPurpose] = useState<Purpose>('login');
  const [channel, setChannel] = useState<'phone' | 'email'>('phone');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const contact = channel === 'phone' ? '+880' + phone : email;
  const [verificationId, setVerificationId] = useState('');
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [role, setRole] = useState<'farmer' | 'customer'>('customer');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const signup = useRef<SignupProfile | undefined>(undefined);
  const options = useQuery({
    queryKey: ['auth-options'],
    queryFn: () => request<{otp: boolean; demo: boolean; signup: boolean}>('/auth/options'),
  });

  function finish({token, user}: {token: string; user: {role: Role}}) {
    setSessionToken(token);
    const dest = user.role === 'admin' ? 'marketplace/admin'
      : marketplace || user.role === 'customer' ? 'marketplace' : 'dashboard';
    window.location.assign(`/${locale}/${dest}`);
  }

  async function run(action: () => Promise<void>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Please try again.', 'আবার চেষ্টা করুন।'));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fields = new FormData(e.currentTarget);
    await run(async () => {
      if (!verificationId) {
        if (purpose === 'signup') {
          const password = String(fields.get('password') || '');
          const confirmPassword = String(fields.get('confirm_password') || '');
          if (password !== confirmPassword) throw new Error(t('Passwords must match.', 'পাসওয়ার্ড দুটি মিলতে হবে।'));
          const photo = fields.get('photo');
          if (!(photo instanceof File) || !photo.size || photo.size > 1024 * 1024) {
            throw new Error(t('Choose a portrait photo up to 1 MB.', 'সর্বোচ্চ ১ এমবির একটি পাসপোর্ট আকারের ছবি বেছে নিন।'));
          }
          signup.current = {
            name, age: Number(age), role,
            national_id: String(fields.get('national_id') || ''),
            permanent_address: String(fields.get('permanent_address') || ''),
            present_address: String(fields.get('present_address') || ''),
            ward_number: String(fields.get('ward_number') || ''),
            gender: String(fields.get('gender') || ''),
            photo_base64: await photoBase64(photo),
            password,
            confirm_password: confirmPassword,
          };
        }
        const result = await request<{verification_id: string}>('/auth/otp/start', {
          method: 'POST',
          body: JSON.stringify({contact, purpose}),
        });
        setVerificationId(result.verification_id);
        return;
      }
      const result = await request<Parameters<typeof finish>[0]>('/auth/otp/verify', {
        method: 'POST',
        body: JSON.stringify({
          contact, purpose, verification_id: verificationId, code: fields.get('code'),
          ...(purpose === 'signup' ? {profile: signup.current} : {}),
        }),
      });
      signup.current = undefined;
      finish(result);
    });
  }

  return <main className="account-access">
    <section className="account-brand">
      <div className="account-mark"><Leaf size={24}/> AgroSphere AI</div>
      <h1>{t('From farm to market', 'খামার থেকে বাজারে')}</h1>
      <p>{t('Screen crop leaves, sell your harvest, or buy directly from growers.', 'ফসলের পাতা পরীক্ষা করুন, ফসল বিক্রি করুন অথবা কৃষকের কাছ থেকে কিনুন।')}</p>
      <Link className="account-language" href={`/${locale === 'en' ? 'bn' : 'en'}${marketplace ? '/marketplace/auth' : ''}`}>
        {locale === 'en' ? 'বাংলা' : 'English'}
      </Link>
    </section>
    <section className="account-form" aria-labelledby="account-title">
      <div className="account-mode" aria-label={t('Account options', 'অ্যাকাউন্টের বিকল্প')}>
        {(['login', 'signup'] as const).map(mode => <button key={mode} type="button"
          aria-pressed={purpose === mode} disabled={busy} onClick={() => {
            signup.current = undefined;
            setPurpose(mode);
            setVerificationId('');
            setError('');
          }}>
          {mode === 'login' ? t('Sign in', 'প্রবেশ করুন') : t('Sign up', 'অ্যাকাউন্ট খুলুন')}
        </button>)}
      </div>
      <h2 id="account-title">{purpose === 'signup' ? t('Create your account', 'অ্যাকাউন্ট তৈরি করুন') : t('Sign in to AgroSphere', 'অ্যাগ্রোস্ফিয়ারে প্রবেশ করুন')}</h2>
      {options.data && !options.data.otp && <p className="notice" role="status">
        {t('Email and SMS codes are unavailable on this server until the verification provider is configured.', 'যাচাই সেবা সেটআপ না হওয়া পর্যন্ত এই সার্ভারে ইমেইল ও এসএমএস কোড পাঠানো যাবে না।')}
      </p>}
      {purpose === 'signup' && options.data?.otp && !options.data.signup && <p className="notice" role="status">
        {t('Signup is unavailable until private identity storage is configured.', 'পরিচয়ের তথ্য নিরাপদে সংরক্ষণের ব্যবস্থা হলে নিবন্ধন চালু হবে।')}
      </p>}
      {options.isError && <p className="error" role="alert">{t('Could not load sign-in options.', 'প্রবেশের বিকল্পগুলো লোড হয়নি।')} <button onClick={() => void options.refetch()}>{t('Retry', 'আবার চেষ্টা')}</button></p>}
      <form onSubmit={submit} className="account-fields">
        {purpose === 'signup' && <>
          <label>{t('Full name', 'পুরো নাম')}<input autoComplete="name" value={name} onChange={e => setName(e.target.value)} maxLength={120} required disabled={busy || !!verificationId}/></label>
          <label>{t('Age in years', 'বয়স (বছর)')}<input type="number" min={1} max={120} step={1} value={age} onChange={e => setAge(e.target.value)} required disabled={busy || !!verificationId}/></label>
          <label>{t('Account type', 'অ্যাকাউন্টের ধরন')}<select value={role} onChange={e => setRole(e.target.value === 'farmer' ? 'farmer' : 'customer')} disabled={busy || !!verificationId}>
            <option value="customer">{t('Customer · Buy produce', 'ক্রেতা · পণ্য কিনুন')}</option>
            <option value="farmer">{t('Farmer · Sell produce and use AgroDoctor', 'কৃষক · পণ্য বিক্রি ও অ্যাগ্রোডক্টর ব্যবহার করুন')}</option>
          </select></label>
          <fieldset className="account-identity" disabled={busy || !!verificationId}>
            <legend>{t('Private signup details', 'নিবন্ধনের ব্যক্তিগত তথ্য')}</legend>
            <label>{t('Bangladesh national ID number', 'বাংলাদেশের জাতীয় পরিচয়পত্র নম্বর')}
              <input name="national_id" inputMode="numeric" autoComplete="off" maxLength={17}
                pattern="(?:[0-9০-৯]{10}|[0-9০-৯]{13}|[0-9০-৯]{17})" required/>
            </label>
            <label>{t('Gender', 'লিঙ্গ')}<select name="gender" defaultValue="" required>
              <option value="" disabled>{t('Choose an option', 'বেছে নিন')}</option>
              <option value="male">{t('Male', 'পুরুষ')}</option>
              <option value="female">{t('Female', 'মহিলা')}</option>
            </select></label>
            <label>{t('Permanent address', 'স্থায়ী ঠিকানা')}<textarea name="permanent_address" rows={2} minLength={5} maxLength={500} required/></label>
            <label>{t('Present address', 'বর্তমান ঠিকানা')}<textarea name="present_address" rows={2} minLength={5} maxLength={500} required/></label>
            <label>{t('Ward number', 'ওয়ার্ড নম্বর')}<input name="ward_number" inputMode="numeric" pattern="[0-9]{1,4}" required/></label>
            <label>{t('Passport-size photo', 'পাসপোর্ট আকারের ছবি')}<input name="photo" type="file" accept="image/jpeg,image/png,image/webp" required/></label>
            <small>{t('JPG, PNG, or WebP up to 1 MB. These details stay private.', 'জেপিজি, পিএনজি বা ওয়েবপি, সর্বোচ্চ ১ এমবি। এই তথ্য ব্যক্তিগত থাকবে।')}</small>
            <label>{t('Set password', 'পাসওয়ার্ড দিন')}<input name="password" type="password" autoComplete="new-password" minLength={10} maxLength={128} required/></label>
            <label>{t('Confirm password', 'পাসওয়ার্ড আবার লিখুন')}<input name="confirm_password" type="password" autoComplete="new-password" minLength={10} maxLength={128} required/></label>
          </fieldset>
        </>}
        <label>{t('Receive code by', 'কোড পাওয়ার মাধ্যম')}<select
          value={channel} disabled={busy || !!verificationId} onChange={e => {
            setChannel(e.target.value === 'email' ? 'email' : 'phone');
            setError('');
          }}
        >
          <option value="phone">{t('Mobile number', 'মোবাইল নম্বর')}</option>
          <option value="email">{t('Email', 'ইমেইল')}</option>
        </select></label>
        {channel === 'phone' ? <label>
          {t('Mobile number', 'মোবাইল নম্বর')}
          <span className="account-phone">
            <span aria-hidden="true">+880</span>
            <input type="tel" autoComplete="tel-national" inputMode="numeric" value={phone}
              onChange={e => setPhone(e.target.value.replace(/[০-৯]/g, digit => String(digit.charCodeAt(0) - 0x09e6)))}
              pattern="1[0-9]{9}" required disabled={busy || !!verificationId} aria-describedby="bd-phone-hint"
              title={t('Enter 10 digits starting with 1 after +880', '+৮৮০ এর পরে ১ দিয়ে শুরু ১০টি সংখ্যা লিখুন')}/>
          </span>
          <small id="bd-phone-hint">{t('Enter 10 digits starting with 1 after +880.', '+৮৮০ এর পরে ১ দিয়ে শুরু ১০টি সংখ্যা লিখুন।')}</small>
        </label> : <label>
          {t('Email address', 'ইমেইল ঠিকানা')}
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email"
            autoCapitalize="none" spellCheck={false} maxLength={254} required disabled={busy || !!verificationId}
            placeholder="name@gmail.com"/>
        </label>}
        {verificationId && <>
          <p role="status">{t('Enter the code sent to your phone or email.', 'ফোন বা ইমেইলে পাঠানো কোডটি লিখুন।')}</p>
          <label>{t('Verification code', 'যাচাই কোড')}<input key={verificationId} name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{4,10}" maxLength={10} required disabled={busy}/></label>
          <button className="text-link" type="button" disabled={busy} onClick={() => {signup.current = undefined; setVerificationId(''); setError('');}}>
            {t('Edit details or request a new code', 'তথ্য বদলান অথবা নতুন কোড চান')}
          </button>
        </>}
        <button className="btn primary" disabled={busy || !options.data?.otp || purpose === 'signup' && !options.data.signup}>
          {verificationId ? t('Verify and continue', 'যাচাই করে এগিয়ে যান') : t('Send verification code', 'যাচাই কোড পাঠান')}<ArrowRight size={16}/>
        </button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {purpose === 'login' && <details className="account-alternative">
        <summary>{t('Sign in with a password', 'পাসওয়ার্ড দিয়ে প্রবেশ করুন')}</summary>
        <form className="account-fields" onSubmit={e => {
          e.preventDefault();
          const fields = new FormData(e.currentTarget);
          void run(async () => finish(await request<Parameters<typeof finish>[0]>('/auth/password', {
            method: 'POST',
            body: JSON.stringify(Object.fromEntries(fields)),
          })));
        }}>
          <label>{t('Phone number or email', 'ফোন নম্বর বা ইমেইল')}<input name="contact" autoComplete="username" required/></label>
          <label>{t('Password', 'পাসওয়ার্ড')}<input name="password" type="password" autoComplete="current-password" required/></label>
          <button className="btn secondary" disabled={busy}>{t('Sign in with password', 'পাসওয়ার্ড দিয়ে প্রবেশ করুন')}</button>
        </form>
      </details>}
      {options.data?.demo && !marketplace && <button type="button" className="btn secondary" disabled={busy}
        onClick={() => void run(async () => {
          const {token} = await request<{token: string}>('/auth/demo', {
            method: 'POST', body: JSON.stringify({name: t('Demo farmer', 'ডেমো কৃষক')}),
          });
          finish({token, user: {role: 'farmer'}});
        })}>
        <ShieldCheck size={16}/>{t('Explore a demo farm', 'ডেমো খামার দেখুন')}
      </button>}
    </section>
  </main>;
}

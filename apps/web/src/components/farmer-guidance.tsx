import {useId} from 'react';
import {Leaf, Phone, Sprout} from 'lucide-react';
import {adviserSource, adviserSummaryBn, farmerGuidance, initialFarmerContext, scoutingSource} from '@/lib/farmer-guidance';
import type {Locale} from '@/lib/messages';
import type {DoctorScreening, FarmerContext} from '@/lib/types';
import {ReadAdvice} from './read-advice';
import styles from './farmer-guidance.module.css';

type Option<T extends string> = [value: T, label: string];

function Choices<T extends string>({question, value, options, onChange, disabled}: {
  question: string; value: T; options: Option<T>[]; onChange: (value: T) => void; disabled?: boolean;
}) {
  const group = useId();
  return <fieldset className={styles.group} disabled={disabled}>
    <legend>{question}</legend>
    <div className={styles.options}>{options.map(([key, label]) =>
      <label className={styles.choice} key={key}>
        <input type="radio" name={group} value={key} checked={key === value} onChange={() => onChange(key)}/>
        {key === 'leaf' && <Leaf size={17} aria-hidden="true"/>}
        {key === 'produce' && <Sprout size={17} aria-hidden="true"/>}
        {label}
      </label>
    )}</div>
  </fieldset>;
}

export function FarmerQuestions({value: answer, onChange, locale, disabled, leafOnly}: {
  value?: FarmerContext; onChange: (next?: FarmerContext) => void; locale: Locale; disabled?: boolean; leafOnly?: boolean;
}) {
  const t = (en: string, bn: string) => locale === 'bn' ? bn : en;
  const value = answer ?? initialFarmerContext;
  const leaf = leafOnly || value.kind === 'leaf';
  const unknown = t('Not sure', 'জানি না');
  const partChoice = !leafOnly && <Choices<FarmerContext['kind'] | 'auto'> question={t('Which part are you checking?', 'কোন অংশটি পরীক্ষা করবেন?')}
      value={answer?.kind ?? 'auto'} options={[['auto', t('Identify from the photo', 'ছবি দেখে শনাক্ত করুন')], ['leaf', t('Leaf', 'পাতা')], ['produce', t('Fruit, vegetable or tuber', 'ফল, সবজি বা কন্দ')]]}
      onChange={kind => onChange(kind === 'auto' ? undefined : {...initialFarmerContext, kind})} disabled={disabled}/>;
  if (!leafOnly && !answer) return <div className={styles.questions}>{partChoice}</div>;
  return <div className={styles.questions}>
    {partChoice}
    {leaf ?
      <Choices<FarmerContext['onset']> question={t('When did you first notice it?', 'প্রথম কবে লক্ষ করেছেন?')}
        value={value.onset}
        options={[['today', t('Today', 'আজ')], ['days', t('A few days ago', 'কয়েক দিন আগে')], ['week_plus', t('A week or more ago', 'এক সপ্তাহ বা তারও আগে')], ['unknown', unknown]]}
        onChange={onset => onChange({...value, onset})} disabled={disabled}/> :
      <Choices<FarmerContext['location']> question={t('Where did you first notice it?', 'প্রথম কোথায় লক্ষ করেছেন?')}
        value={value.location} options={[['field', t('In the field', 'খেতে')], ['storage', t('In storage', 'সংরক্ষণের সময়')], ['unknown', unknown]]}
        onChange={location => onChange({...value, location})} disabled={disabled}/>}
    <Choices<FarmerContext['extent']> question={leaf ? t('How many plants look affected?', 'কয়টি গাছে এমন দেখেছেন?') : t('How many items look affected?', 'কয়টি ফল, সবজি বা কন্দে এমন দেখেছেন?')}
      value={value.extent} options={leaf
        ? [['one', t('One plant', 'একটি গাছে')], ['several', t('Several plants', 'কয়েকটি গাছে')], ['many', t('Many plants', 'অনেক গাছে')], ['unknown', unknown]]
        : [['one', t('One item', 'একটিতে')], ['several', t('Several items', 'কয়েকটিতে')], ['many', t('Many items', 'অনেকগুলোতে')], ['unknown', unknown]]}
      onChange={extent => onChange({...value, extent})} disabled={disabled}/>
  </div>;
}

export function FarmerActionCard({result, locale}: {result: DoctorScreening; locale: Locale}) {
  const t = (en: string, bn: string) => locale === 'bn' ? bn : en;
  const advice = farmerGuidance(result, locale);
  const heading = useId();
  return <section aria-labelledby={heading} className={styles.card}>
    <h2 id={heading}>{t('What should I do today?', 'আজ কী করব?')}</h2>
    <p className={styles.action}>{advice.action}</p>
    {advice.checks.length > 0 && <ul className={styles.checks}>{advice.checks.map(check => <li key={check}>{check}</li>)}</ul>}
    <p className={styles.reason}><strong>{t('Why?', 'কেন?')}</strong> {advice.reason}</p>
    <ReadAdvice locale={locale} text={advice.speech}/>
    {advice.refer && <div className={styles.referral}>
      <a className={'btn primary ' + styles.call} href="tel:16123">
        <Phone size={18} aria-hidden="true"/>{t('Call the Agriculture Call Centre · 16123', 'কৃষি কল সেন্টারে ফোন করুন · ১৬১২৩')}
      </a>
      <h3>{t('What to tell the adviser in Bangla', 'কৃষি কর্মকর্তাকে যা বলবেন')}</h3>
      <p className={styles.summary} lang="bn">{adviserSummaryBn(result)}</p>
    </div>}
    <div className={styles.sources}>
      <a href={advice.source} target="_blank" rel="noreferrer">{advice.source === scoutingSource
        ? t('Photo guidance · University of Minnesota Extension', 'ছবি তোলার নির্দেশনা · মিনেসোটা বিশ্ববিদ্যালয় এক্সটেনশন')
        : t('Early blight field guide · University of Minnesota Extension', 'আগাম ধসা রোগের মাঠ নির্দেশিকা · মিনেসোটা বিশ্ববিদ্যালয় এক্সটেনশন')}</a>
      {advice.refer && <a href={adviserSource} target="_blank" rel="noreferrer">{t('Call centre information · Bangladesh Agricultural Information Service', 'কল সেন্টারের তথ্য · বাংলাদেশ কৃষি তথ্য সার্ভিস')}</a>}
    </div>
  </section>;
}

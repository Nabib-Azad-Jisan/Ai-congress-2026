import {useId} from 'react';
import {ArrowUpRight, MapPin} from 'lucide-react';
import {ApiError} from '@/lib/api';
import type {DistrictPrices, MarketCrop} from '@/lib/marketplace-types';
import {useMarket, useMarketQuery} from './marketplace-shared';
import './district-price-card.css';

const unitLabels: Record<string, string> = {kg:'কেজি', g:'গ্রাম', piece:'পিস', bundle:'আঁটি', crate:'ক্রেট'};

export function DistrictPriceCard({crop, district, listingUnit}: {
  crop?: MarketCrop;
  district: string;
  listingUnit: string;
}) {
  const {locale, t} = useMarket();
  const heading = useId();
  const unit = listingUnit === 'g' ? 'kg' : listingUnit;
  const unitLabel = t(unit, unitLabels[unit] || unit);
  const params = new URLSearchParams({crop:crop?.id || '', district, unit});
  const prices = useMarketQuery<DistrictPrices>('/market/district-prices?' + params, Boolean(crop && district));
  const numberLocale = locale === 'bn' ? 'bn-BD' : 'en-BD';
  const money = new Intl.NumberFormat(numberLocale, {minimumFractionDigits:2, maximumFractionDigits:2});
  const dates = new Intl.DateTimeFormat(numberLocale, {day:'numeric',month:'short',year:'numeric',timeZone:'Asia/Dhaka'});
  const data = prices.data;
  const invalidDistrict = prices.error instanceof ApiError && prices.error.status === 422;

  return <aside className="mk-district-card" aria-labelledby={heading}>
    <h3 id={heading}>{t('Recent prices in my district','আমার জেলার সাম্প্রতিক দাম')}</h3>
    {district && <p className="mk-district-location"><MapPin size={14} aria-hidden="true"/>
      {[district, crop?.[locale], unitLabel].filter(Boolean).join(' · ')}
    </p>}
    <div aria-live="polite" aria-atomic="true">
      {!district ? <p>{t('Select a farm or add your district in Profile to see local prices.',
        'স্থানীয় দাম দেখতে খামার বেছে নিন অথবা প্রোফাইলে আপনার জেলা দিন।')}</p>
        : !crop ? <p>{t('Choose a crop to see prices for this district.','এই জেলার দাম দেখতে একটি ফসল বেছে নিন।')}</p>
        : prices.isError ? <div role="alert">
          {invalidDistrict
            ? <p>{t('This district could not be matched to a Bangladesh district.','এই নামটি বাংলাদেশের কোনো জেলার সঙ্গে মেলেনি।')}</p>
            : <><p>{t('Local prices could not be loaded.','স্থানীয় দাম লোড করা যায়নি।')}</p>
              <button type="button" onClick={() => void prices.refetch()}>{t('Retry','আবার চেষ্টা করুন')}</button></>}
        </div>
        : !data ? <p>{t('Loading local prices…','স্থানীয় দাম লোড হচ্ছে…')}</p>
        : <>
          <p className="mk-district-dates">{t('Last 30 days','গত ৩০ দিন')}{' · '}
            <time dateTime={data.window_start}>{dates.format(new Date(data.window_start))}</time>
            {' – '}<time dateTime={data.window_end}>{dates.format(new Date(data.window_end))}</time></p>
          <dl className="mk-district-stats">
            {(['asking','agreed'] as const).map(kind => {
              const {count, median_bdt} = data[kind];
              const asking = kind === 'asking';
              const samples = count.toLocaleString(numberLocale);
              const sourceCount = asking
                ? t(`${samples} ${count === 1 ? 'listing' : 'listings'}`, `${samples}টি পণ্য তালিকা`)
                : t(`${samples} ${count === 1 ? 'order' : 'orders'}`, `${samples}টি অর্ডার`);
              return <div key={kind}>
                <dt>{asking ? t('Median asking price','বিক্রেতার চাওয়া দামের মধ্যক')
                  : t('Median agreed order price','অর্ডারে সম্মত দামের মধ্যক')} <small>{sourceCount}</small></dt>
                <dd>{median_bdt === null
                  ? <span>{asking ? t('Not enough local listings yet.','এই জেলায় এখনও পর্যাপ্ত পণ্য তালিকা নেই।')
                    : t('Not enough local orders yet.','এই জেলায় এখনও পর্যাপ্ত অর্ডার নেই।')}</span>
                  : <><strong>{money.format(Number(median_bdt))}</strong> {t('BDT','টাকা')} / {unitLabel}</>}</dd>
              </div>;
            })}
          </dl>
          <p>{t(`Each median needs at least ${data.min_samples} records.`,
            `মধ্যক দেখাতে প্রতিটি ক্ষেত্রে অন্তত ${data.min_samples.toLocaleString(numberLocale)}টি রেকর্ড প্রয়োজন।`)}
            {listingUnit === 'g' && ' ' + t('Gram prices are shown per kg.','গ্রামের দাম কেজি প্রতি দেখানো হয়েছে।')}</p>
        </>}
    </div>
    <footer>
      <p>{t('KrishiMarket listings and seller-confirmed orders. Payments are recorded in demo mode.',
        'কৃষিমার্কেটের পণ্য তালিকা ও বিক্রেতার নিশ্চিত করা অর্ডার। পেমেন্টের হিসাব ডেমো মোডে রাখা হয়।')}</p>
      <a href="https://market.dam.gov.bd/market_daily_price_report" target="_blank" rel="noopener noreferrer">
        {t('Official market reports (DAM)','সরকারি বাজারদর (কৃষি বিপণন অধিদপ্তর)')} <ArrowUpRight size={14} aria-hidden="true"/>
      </a>
    </footer>
  </aside>;
}

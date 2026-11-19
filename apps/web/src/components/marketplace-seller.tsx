'use client';
import {useEffect,useState,type FormEvent} from 'react';
import {request} from '@/lib/api';
import type {Farm} from '@/lib/types';
import type {Auction,FarmerDashboard,MarketCrop,Product} from '@/lib/marketplace-types';
import {useMarket,useMarketQuery,send,cash,Field,Panel,DataState,Empty,ProductImage,ProductVideo} from './marketplace-shared';
import {DistrictPriceCard} from './district-price-card';
import Link from 'next/link';
import {AuctionBox,OrderCard} from './marketplace-commerce';

export function MarketplaceSeller(){const {t,locale,busy,perform}=useMarket();const q=useMarketQuery<FarmerDashboard>('/market/farmer/dashboard',true,15000);const [editing,setEditing]=useState<Product|null|undefined>();const [auctionProduct,setAuctionProduct]=useState<Product|null>(null);const [editAuction,setEditAuction]=useState<Auction|null>(null);
 return <><div className="mk-section-heading"><div><span className="mk-kicker">{t('YOUR GROWER SPACE','আপনার কৃষক স্টুডিও')}</span><h1>{t('Seller studio','বিক্রেতা স্টুডিও')}</h1></div><button aria-label={t('New listing','নতুন পণ্য')} className="mk-primary" disabled={busy} onClick={()=>setEditing(null)}>+ {t('New listing','নতুন পণ্য')}</button></div><DataState query={q}/>{q.data&&<><div className="mk-stats"><Panel title={t('Harvest listings','পণ্যের তালিকা')}><strong>{q.data.products.length}</strong></Panel><Panel title={t('Orders','অর্ডার')}><strong>{q.data.orders.length}</strong></Panel><Panel title={t('Auction lots','নিলামের লট')}><strong>{q.data.auctions.length}</strong></Panel></div>
 <section aria-label={t('Recent orders','সাম্প্রতিক অর্ডার')}>
  <div className="mk-section-heading"><h2>{t('Recent orders','সাম্প্রতিক অর্ডার')}</h2>
   <Link href={`/${locale}/marketplace/orders`}>{t('View all orders','সব অর্ডার দেখুন')}</Link></div>
  {q.data.orders.slice(0,3).map(order=><OrderCard order={order} key={order.id}/>)}
  {!q.data.orders.length&&<Empty>{t('Customer orders will appear here.','ক্রেতাদের অর্ডার এখানে দেখা যাবে।')}</Empty>}
 </section>
 {!q.data.profile?.district&&<p className="mk-note">{t('Your listing uses the selected farm’s district. You can also set a district in Profile.','পণ্য তালিকায় নির্বাচিত খামারের জেলা ব্যবহার করা হবে। চাইলে প্রোফাইলেও জেলা দিতে পারেন।')}</p>}{editing!==undefined&&<ListingEditor key={editing?.id||'new'} product={editing} profileDistrict={q.data.profile?.district || ''} onClose={()=>setEditing(undefined)}/>}<h2>{t('Your produce','আপনার পণ্য')}</h2><div className="mk-products">{q.data.products.map(p=><article className="mk-product" key={p.id}><div className="mk-product-photo"><ProductImage product={p}/></div><div className="mk-product-copy"><h3>{p.name}</h3><p>{cash(p.price_bdt)} / {p.unit} · {p.stock_quantity} {p.unit}</p><p><span className="mk-badge">{p.status}</span> · {p.moderation_status}</p><p className="mk-muted">{t('Reserved for auction','নিলামের জন্য সংরক্ষিত')}: {p.auction_reserved} {p.unit}</p><div className="mk-row"><button disabled={busy} onClick={()=>setEditing(p)}>{t('Edit listing','পণ্য সম্পাদনা')}</button>{p.status!=='archived'&&<button disabled={busy} onClick={()=>void perform(()=>send('/market/products/'+p.id,{status:'archived',expected_version:p.version},'PATCH'))}>{t('Archive','আর্কাইভ')}</button>}<button disabled={busy||p.status!=='published'} onClick={()=>{setAuctionProduct(p);setEditAuction(null);}}>{t('Create optional auction','ঐচ্ছিক নিলাম তৈরি')}</button></div></div></article>)}</div>{!q.data.products.length&&<Empty>{t('Publish your first harvest with a clear price, quantity and collection method.','সঠিক দাম, পরিমাণ ও সংগ্রহ পদ্ধতি দিয়ে প্রথম পণ্য প্রকাশ করুন।')}</Empty>}{(auctionProduct||editAuction)&&<AuctionEditor product={auctionProduct} auction={editAuction} onClose={()=>{setAuctionProduct(null);setEditAuction(null);}}/>}<h2>{t('Your auctions','আপনার নিলাম')}</h2>{q.data.auctions.map(a=><div key={a.id}><AuctionBox auction={a}/><div className="mk-row">{a.state==='draft'&&<><button disabled={busy} onClick={()=>{setAuctionProduct(q.data!.products.find(p=>p.id===a.product_id)||null);setEditAuction(a);}}>{t('Edit draft','খসড়া সম্পাদনা')}</button><button disabled={busy} onClick={()=>void perform(()=>send('/market/auctions/'+a.id+'/publish',{}))}>{t('Publish auction','নিলাম প্রকাশ')}</button></>}{['draft','scheduled','live','awarded'].includes(a.state)&&<CancelAuction auction={a}/>}</div></div>)}<details><summary>{t('Seller analytics','বিক্রেতার পরিসংখ্যান')}</summary><div className="mk-metrics">{Object.entries(q.data.sales||{}).map(([key,value])=><div key={key}><span>{key.replaceAll('_',' ')}</span><strong>{typeof value==='object'?JSON.stringify(value):String(value)}</strong></div>)}</div></details></>}</>;
}
function ListingEditor({product:p,profileDistrict,onClose}:{product:Product|null;profileDistrict:string;onClose:()=>void}){const {t,busy,perform}=useMarket();const farms=useMarketQuery<Farm[]>('/farms');const [saved,setSaved]=useState<Product|null>(p);const [delivery,setDelivery]=useState(p?.delivery_enabled||false);const [nationwide,setNationwide]=useState(p?.nationwide_delivery||false);const current=useMarketQuery<Product>('/market/products/'+saved?.id,!!saved);
 const crops=useMarketQuery<{items:MarketCrop[]}>('/market/district-prices/crops');
 const [farmId,setFarmId]=useState(p?.farm_id || '');
 const [commodity,setCommodity]=useState(p?.commodity || '');
 const [unit,setUnit]=useState(p?.unit || 'kg');
 const district = saved?.district || profileDistrict || farms.data?.find(f => f.id === farmId)?.district || '';
 const selectedCrop = crops.data?.items.find(crop => crop.id === commodity);
 const [photo,setPhoto]=useState<File>();const [video,setVideo]=useState<File>();
 useEffect(()=>{if(current.data)setSaved(current.data);},[current.data]);
 async function save(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);const body:Record<string,unknown>=Object.fromEntries(f);for(const name of ['minimum_order_quantity','maximum_order_quantity','harvest_date','available_from'])if(!body[name])body[name]=null;for(const name of ['pickup_enabled','delivery_enabled','nationwide_delivery'])body[name]=f.get(name)==='on';body.delivery_districts=String(f.get('delivery_districts')||'').split(',').map(v=>v.trim()).filter(Boolean);if(saved)body.expected_version=saved.version;
 if(commodity !== (saved?.commodity || '')) body.commodity = commodity || null;
 await perform(async()=>{
  const next=await send<Product>('/market/products'+(saved?'/'+saved.id:''),body,saved?'PATCH':'POST');
  setSaved(next);
  setCommodity(next.commodity || '');
  if(photo){await uploadFile(next.id,'image',photo);setPhoto(undefined);}
  if(video){await uploadFile(next.id,'video',video);setVideo(undefined);}
 },t('Listing saved.','পণ্য সংরক্ষিত।'));}
 function uploadFile(id:string,kind:'image'|'video',file:File){
  const body=new FormData();
  body.append(kind,file);
  return request('/market/products/'+id+(kind==='image'?'/images':'/videos'),{method:'POST',body});
 }
 async function upload(e:FormEvent<HTMLFormElement>,kind:'image'|'video'){
  e.preventDefault();const el=e.currentTarget;
  const file=new FormData(el).get(kind);
  if(!saved||!(file instanceof File)||!file.size)return;
  const ok=await perform(()=>uploadFile(saved.id,kind,file),kind==='image'?t('Photo added.','ছবি যোগ হয়েছে।'):t('Video added.','ভিডিও যোগ হয়েছে।'));
  if(ok)el.reset();
 }
 return <Panel title={saved?t('Edit harvest listing','পণ্য সম্পাদনা'):t('New harvest listing','নতুন পণ্যের তালিকা')}><button className="mk-text-button" onClick={onClose}>{t('Close editor','সম্পাদনা বন্ধ')}</button><DataState query={farms}/>{farms.data&&!farms.data.length&&<div className="mk-inset"><h3>{t('Create your farm first','প্রথমে খামার তৈরি করুন')}</h3><form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);void perform(()=>send('/farms',{name:f.get('name'),district:f.get('district')}),t('Farm created. Select it below.','খামার তৈরি হয়েছে। নিচে নির্বাচন করুন।'));}}><Field label={t('Farm name','খামারের নাম')}><input name="name" required maxLength={100}/></Field><Field label={t('Farm district','খামারের জেলা')}><input name="district" required maxLength={80}/></Field><button disabled={busy}>{t('Create farm','খামার তৈরি')}</button></form></div>}<form onSubmit={save}><Field label={t('Farm','খামার')}><select name="farm_id" required value={farmId} onChange={e=>setFarmId(e.target.value)}><option value="">{t('Select your farm','আপনার খামার বাছুন')}</option>{farms.data?.map(f=><option value={f.id} key={f.id}>{f.name} · {f.district}</option>)}</select></Field><div className="mk-grid"><Field label={t('Product name','পণ্যের নাম')}><input name="name" required maxLength={120} defaultValue={p?.name}/></Field><Field label={t('Category','বিভাগ')}><select name="category" defaultValue={p?.category||'vegetables'}>{['vegetables','fruits','rice_grains','pulses','other'].map((v,i)=><option key={v} value={v}>{t(['Vegetables','Fruits','Rice & grains','Pulses','Other'][i],['সবজি','ফল','চাল ও শস্য','ডাল','অন্যান্য'][i])}</option>)}</select></Field></div><Field label={t('Description','বর্ণনা')}><textarea name="description" required maxLength={3000} defaultValue={p?.description}/></Field>
 <div className="mk-listing-pricing">
  <div>
   <Field label={t('Crop (optional)','ফসল (ঐচ্ছিক)')}>
    <select value={commodity} onChange={e=>setCommodity(e.target.value)} disabled={!crops.data}>
     <option value="">{t('Select a crop','একটি ফসল বেছে নিন')}</option>
     {commodity&&!selectedCrop&&<option value={commodity}>{commodity}</option>}
     {crops.data?.items.map(crop=><option key={crop.id} value={crop.id}>{t(crop.en,crop.bn)}</option>)}
    </select>
   </Field>
   {crops.isPending&&<p role="status">{t('Loading crops…','ফসলের তালিকা লোড হচ্ছে…')}</p>}
   {crops.isError&&<div className="mk-error" role="alert">
    {t('The crop list could not be loaded.','ফসলের তালিকা লোড করা যায়নি।')}{' '}
    <button type="button" onClick={()=>void crops.refetch()}>{t('Retry','আবার চেষ্টা করুন')}</button>
   </div>}
   <div className="mk-grid">
    <Field label={t('Price (BDT)','দাম (টাকা)')}><input name="price_bdt" type="number" min="0.01" step="0.01" required defaultValue={p?.price_bdt}/></Field>
    <Field label={t('Unit','একক')}>
     <select name="unit" value={unit} onChange={e=>setUnit(e.target.value)}>
      {['kg','g','piece','bundle','crate'].map((v,i)=><option key={v} value={v}>{t(v,['কেজি','গ্রাম','পিস','আঁটি','ক্রেট'][i])}</option>)}
     </select>
    </Field>
    <Field label={t('Quantity step','পরিমাণের ধাপ')}><input name="quantity_step" type="number" step="0.001" min="0.001" required defaultValue={p?.quantity_step||'1'}/></Field><Field label={t('Stock quantity','মজুত পরিমাণ')}><input name="stock_quantity" type="number" step="0.001" min="0" required defaultValue={p?.stock_quantity||'0'}/></Field>
   </div>
  </div>
  <DistrictPriceCard crop={selectedCrop} district={district} listingUnit={unit}/>
 </div>
 <div className="mk-grid"><Field label={t('Minimum order quantity (optional)','ন্যূনতম অর্ডার পরিমাণ (ঐচ্ছিক)')}><input name="minimum_order_quantity" type="number" step="0.001" min="0.001" defaultValue={p?.minimum_order_quantity||''}/></Field><Field label={t('Maximum order quantity (optional)','সর্বোচ্চ অর্ডার পরিমাণ (ঐচ্ছিক)')}><input name="maximum_order_quantity" type="number" step="0.001" min="0.001" defaultValue={p?.maximum_order_quantity||''}/></Field><Field label={t('Harvest date','ফসল সংগ্রহের তারিখ')}><input type="date" name="harvest_date" defaultValue={p?.harvest_date?.slice(0,10)||''}/></Field><Field label={t('Available from','বিক্রি শুরুর তারিখ')}><input type="date" name="available_from" defaultValue={p?.available_from?.slice(0,10)||''}/></Field></div><div className="mk-inset"><label className="mk-check"><input name="pickup_enabled" type="checkbox" defaultChecked={p?.pickup_enabled??true}/>{t('Allow farm pickup','খামার থেকে সংগ্রহের সুযোগ')}</label><label className="mk-check"><input name="delivery_enabled" type="checkbox" checked={delivery} onChange={e=>setDelivery(e.target.checked)}/>{t('Offer delivery','ডেলিভারি দিন')}</label>{delivery&&<><label className="mk-check"><input type="checkbox" name="nationwide_delivery" checked={nationwide} onChange={e=>setNationwide(e.target.checked)}/>{t('Deliver nationwide in Bangladesh','সারা বাংলাদেশে ডেলিভারি')}</label>{!nationwide&&<Field label={t('Delivery districts (comma separated)','ডেলিভারি জেলা (কমা দিয়ে লিখুন)')}><input name="delivery_districts" defaultValue={p?.delivery_districts.join(', ')} required/></Field>}<Field label={t('Delivery fee (BDT)','ডেলিভারি ফি (টাকা)')}><input name="delivery_fee_bdt" type="number" min="0" step="0.01" required defaultValue={p?.delivery_fee_bdt||'0'}/></Field></>}{!delivery&&<input type="hidden" name="delivery_fee_bdt" value="0"/>}</div><Field label={t('Pickup instructions (private until order)','সংগ্রহের নির্দেশনা (অর্ডারের আগে ব্যক্তিগত)')}><textarea name="pickup_instructions" maxLength={600} defaultValue={p?.pickup_instructions||''}/></Field>{!saved&&<section className="mk-inset">
 <h3>{t('Product photos and video','পণ্যের ছবি ও ভিডিও')}</h3>
 <p>{t('Optional. Selected files upload when you save the listing. Add more photos after saving.','ঐচ্ছিক। পণ্য সংরক্ষণের সময় নির্বাচিত ফাইল আপলোড হবে। পরে আরও ছবি যোগ করতে পারবেন।')}</p>
 <Field label={t('Product photo','পণ্যের ছবি')}><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e=>setPhoto(e.target.files?.[0])}/></Field>
 <Field label={t('Product video','পণ্যের ভিডিও')}><input type="file" accept=".mp4,.webm,video/mp4,video/webm" onChange={e=>setVideo(e.target.files?.[0])}/></Field>
 <small>{t('Photo up to 8 MB. One MP4 or WebM up to 20 MB.','ছবি সর্বোচ্চ ৮ এমবি। একটি MP4 বা WebM সর্বোচ্চ ২০ এমবি।')}</small>
 </section>}<Field label={t('Listing status','পণ্যের অবস্থা')}><select name="status" defaultValue={p?.status||'draft'}>{['draft','published','paused','archived'].map((v,i)=><option key={v} value={v}>{t(['Draft','Published','Paused','Archived'][i],['খসড়া','প্রকাশিত','স্থগিত','আর্কাইভ'][i])}</option>)}</select></Field><p className="mk-note">{t('Unit, quantity step and farm cannot change after an order or auction. Conflicting edits require refreshing the listing version.','অর্ডার বা নিলামের পরে একক, পরিমাণের ধাপ ও খামার বদলানো যায় না। পরিবর্তনের দ্বন্দ্ব হলে পণ্য হালনাগাদ করুন।')}</p><div className="mk-row"><button disabled={busy} className="mk-primary">{t('Save listing','পণ্য সংরক্ষণ')}</button>{saved&&<button type="button" disabled={busy} onClick={()=>void current.refetch()}>{t('Refresh version','সংস্করণ হালনাগাদ')}</button>}</div></form>{saved&&<section className="mk-inset"><h3>{t('Product gallery (up to 6 photos)','পণ্যের গ্যালারি (সর্বোচ্চ ৬ ছবি)')}</h3><div className="mk-thumbnails">{saved.images.map((im,i)=><div key={im.id}><ProductImage product={saved} index={i}/><button disabled={busy} onClick={()=>void perform(()=>request('/market/products/'+saved.id+'/images/'+im.id,{method:'DELETE'}))}>{t('Remove photo','ছবি মুছুন')}</button></div>)}</div>{saved.images.length<6&&<form onSubmit={e=>void upload(e,'image')}><Field label={t('Product photo','পণ্যের ছবি')}><input type="file" name="image" accept="image/jpeg,image/png,image/webp" required/></Field><button disabled={busy}>{t('Upload photo','ছবি আপলোড')}</button></form>}
 <h3>{t('Product video','পণ্যের ভিডিও')}</h3>
 {saved.videos?.[0]?<>
  <ProductVideo product={saved}/>
  <button type="button" disabled={busy} onClick={()=>void perform(()=>request('/market/products/'+saved.id+'/images/'+saved.videos![0].id,{method:'DELETE'}))}>{t('Remove video','ভিডিও সরান')}</button>
 </>:<form onSubmit={e=>void upload(e,'video')}>
  <Field label={t('Product video','পণ্যের ভিডিও')}><input type="file" name="video" accept=".mp4,.webm,video/mp4,video/webm" required/></Field>
  <p>{t('One MP4 or WebM up to 20 MB.','একটি MP4 বা WebM সর্বোচ্চ ২০ এমবি।')}</p>
  <button disabled={busy}>{t('Upload video','ভিডিও আপলোড')}</button>
 </form>}
 </section>}</Panel>;
}
function localDate(value?:string){if(!value)return '';const d=new Date(value);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function AuctionEditor({product,auction:a,onClose}:{product:Product|null;auction:Auction|null;onClose:()=>void}){const {t,busy,perform}=useMarket();async function save(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);const body:Record<string,unknown>=Object.fromEntries(f);body.product_id=product?.id||a?.product_id;body.starts_at=new Date(String(f.get('starts_at'))).toISOString();body.ends_at=new Date(String(f.get('ends_at'))).toISOString();body.reserve_price_bdt=f.get('reserve_price_bdt')||null;body.draft=f.get('draft')==='on';const ok=await perform(()=>send('/market/auctions'+(a?'/'+a.id:''),body,a?'PATCH':'POST'));if(ok)onClose();}return <Panel title={a?t('Edit auction draft','নিলামের খসড়া সম্পাদনা'):t('Create an optional auction','ঐচ্ছিক নিলাম তৈরি')}><p>{product?.name||a?.product?.name}</p><form onSubmit={save}><div className="mk-grid mk-three">{[['lot_quantity','Lot quantity','লটের পরিমাণ',a?.lot_quantity],['starting_bid_bdt','Starting bid (BDT)','শুরুর বিড (টাকা)',a?.starting_bid_bdt],['minimum_increment_bdt','Minimum increment (BDT)','ন্যূনতম বৃদ্ধি (টাকা)',a?.minimum_increment_bdt],['reserve_price_bdt','Reserve price (optional, private)','সংরক্ষিত দাম (ঐচ্ছিক, ব্যক্তিগত)',a?.reserve_price_bdt]].map(([name,en,bn,value])=><Field label={t(en!,bn!)} key={name}><input name={name!} type="number" min="0.01" step="0.01" required={name!=='reserve_price_bdt'} defaultValue={value||''}/></Field>)}<Field label={t('Auction starts (your local time)','নিলাম শুরু (স্থানীয় সময়)')}><input name="starts_at" type="datetime-local" required defaultValue={localDate(a?.starts_at)}/></Field><Field label={t('Auction ends (your local time)','নিলাম শেষ (স্থানীয় সময়)')}><input name="ends_at" type="datetime-local" required defaultValue={localDate(a?.ends_at)}/></Field></div>{!a&&<label className="mk-check"><input type="checkbox" name="draft" defaultChecked/>{t('Save as draft before publishing','প্রকাশের আগে খসড়া রাখুন')}</label>}<p className="mk-note">{t('Publishing reserves this lot from direct-buy stock. Server time controls bidding and confirmation deadlines. Drafts do not reserve stock.','প্রকাশ করলে লট সরাসরি বিক্রির মজুত থেকে সংরক্ষিত হয়। সার্ভারের সময় বিড ও নিশ্চিতকরণের সময়সীমা নিয়ন্ত্রণ করে। খসড়া মজুত সংরক্ষণ করে না।')}</p><div className="mk-row"><button disabled={busy} className="mk-primary">{t('Save auction','নিলাম সংরক্ষণ')}</button><button type="button" onClick={onClose}>{t('Close','বন্ধ করুন')}</button></div></form></Panel>;}
function CancelAuction({auction:a}:{auction:Auction}){const {t,perform,busy}=useMarket();return <details><summary>{t('Cancel auction','নিলাম বাতিল')}</summary><form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);void perform(()=>send('/market/auctions/'+a.id+'/cancel',{reason:f.get('reason')}));}}><Field label={t('Auction cancellation reason','নিলাম বাতিলের কারণ')}><input name="reason" required maxLength={500}/></Field><button disabled={busy}>{t('Confirm auction cancellation','নিলাম বাতিল নিশ্চিত')}</button></form></details>;}

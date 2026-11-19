import {expect, test, type Page} from '@playwright/test';

const api = (process.env.E2E_API_URL || process.env.AGROSPHERE_API_URL || 'http://127.0.0.1:8300/api/v1').replace(/\/$/, '');

async function sellerSession(page: Page, token: string) {
  await page.addInitScript(value => localStorage.setItem('agrosphere-token', value), token);
}

test('seller sees separate sample counts and no stale price when the listing unit changes', async ({page}) => {
  await sellerSession(page, 'price-card-test');
  let releasePiece!: () => void;
  const waiting = new Promise<void>(resolve => { releasePiece = resolve; });
  let failCrate = true;
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/api/v1', '');
    const farmer = {id:'seller', role:'farmer', name:'Price test farmer', preferences:{language:'en',theme:'light'}};
    switch (path) {
      case '/me':
        return route.fulfill({json: farmer});
      case '/market/farmer/dashboard':
        return route.fulfill({json: {profile:{district:'Gazipur'}, products:[], orders:[], auctions:[], sales:{}}});
      case '/farms':
        return route.fulfill({json: [{id:'farm', name:'North field', district:'Dhaka'}]});
      case '/market/district-prices/crops':
        return route.fulfill({json: {items:[{id:'tomato',en:'Tomato',bn:'টমেটো'}]}});
      case '/market/district-prices': {
        expect(route.request().headers().authorization).toBe('Bearer price-card-test');
        const unit = url.searchParams.get('unit');
        expect(url.searchParams.get('district')).toBe('Gazipur');
        expect(url.searchParams.get('crop')).toBe('tomato');
        if (unit === 'piece') await waiting;
        if (unit === 'crate' && failCrate) return route.fulfill({status:503,json:{message:'Prices unavailable'}});
        return route.fulfill({json:{
          crop:'tomato',district:'Gazipur',unit,currency:'BDT',min_samples:3,
          window_start:'2026-10-01T00:00:00Z',window_end:'2026-10-31T00:00:00Z',
          asking:unit === 'kg' ? {count:4,median_bdt:'56.50'} : {count:0,median_bdt:null},
          agreed:unit === 'crate' ? {count:3,median_bdt:'135.50'} : {count:2,median_bdt:null},
        }});
      }
      default:
        return route.fulfill({json:[]});
    }
  });
  await page.goto('/en/marketplace/seller');
  await page.getByRole('button', {name:'New listing',exact:true}).click();
  const card = page.getByRole('complementary', {name:'Recent prices in my district'});
  await expect(card).toBeVisible();
  await page.getByLabel('Farm', {exact:true}).selectOption('farm');
  await page.getByLabel('Crop (optional)', {exact:true}).selectOption('tomato');
  await expect(card).toContainText('56.50');
  await expect(card).toContainText('4 listings');
  await expect(card).toContainText('2 orders');
  await expect(card).toContainText('Not enough local orders yet.');
  await expect(card).toContainText('Oct');
  await expect(card).toContainText('Gazipur');
  const fieldBox = await page.getByLabel('Price (BDT)', {exact:true}).boundingBox();
  const cardBox = await card.boundingBox();
  expect(cardBox!.x).toBeGreaterThan(fieldBox!.x + fieldBox!.width);
  await expect(card.getByRole('link', {name:/official/i})).toHaveAttribute('href', /^https:\/\/market\.dam\.gov\.bd\//);
  const unit = page.getByLabel('Unit', {exact:true});
  await unit.selectOption('g');
  await expect(card).toContainText('56.50');
  await unit.selectOption('piece');
  try {
    await expect(card).toContainText('Loading local prices');
    await expect(card).not.toContainText('56.50');
    await unit.selectOption('crate');
    await expect(card.getByRole('alert')).toBeVisible();
    failCrate = false;
    await card.getByRole('button', {name:'Retry'}).click();
    await expect(card).toContainText('0 listings');
    await expect(card).toContainText('3 orders');
    await expect(card).toContainText('135.50');
  } finally {
    releasePiece();
  }
  await expect(card).toContainText('crate');
  await expect(card).not.toContainText('piece');
  await page.getByLabel('Crop (optional)', {exact:true}).selectOption('');
  await expect(card).not.toContainText('135.50');
  await expect(card).toContainText('Choose a crop');
});

test('Bengali seller can save a crop and edit it using the saved listing district on a phone', async ({page, request}) => {
  const registration = await request.post(api + '/auth/register', {data:{
    name:'District grower',email:`district-${crypto.randomUUID()}@example.test`,password:'District-test-8274!',role:'farmer',
  }});
  expect(registration.ok(), await registration.text()).toBeTruthy();
  const {token} = await registration.json();
  const headers = {Authorization:`Bearer ${token}`};
  const newFarm = await request.post(api + '/farms', {headers, data:{name:'Local farm',district:'Gazipur'}});
  expect(newFarm.ok(), await newFarm.text()).toBeTruthy();
  const farm = await newFarm.json();
  await sellerSession(page, token);
  await page.setViewportSize({width:375,height:812});
  await page.goto('/bn/marketplace/seller');
  await page.getByRole('button', {name:'নতুন পণ্য',exact:true}).click();
  const card = page.getByRole('complementary', {name:'আমার জেলার সাম্প্রতিক দাম'});
  await page.getByLabel('খামার', {exact:true}).selectOption(farm.id);
  await page.getByLabel('ফসল (ঐচ্ছিক)').selectOption('tomato');
  await expect(card).toContainText('Gazipur');
  await expect(card).toContainText('টমেটো');
  await expect(card).toContainText('মধ্যক');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByLabel('পণ্যের নাম').fill('Field harvest');
  await page.getByLabel('বর্ণনা').fill('Locally grown harvest');
  await page.getByLabel('দাম (টাকা)', {exact:true}).fill('35');
  const saved = page.waitForResponse(r => r.url().endsWith('/market/products') && r.request().method() === 'POST');
  await page.getByRole('button', {name:'পণ্য সংরক্ষণ',exact:true}).click();
  const created = await saved;
  expect(created.ok(), await created.text()).toBeTruthy();
  const listing = await created.json();
  expect(listing.commodity).toBe('tomato');
  const changedProfile = await request.patch(api + '/market/profile', {headers,data:{district:'Dhaka',area:'Savar'}});
  expect(changedProfile.ok(), await changedProfile.text()).toBeTruthy();
  await page.reload();
  await page.getByRole('button', {name:'পণ্য সম্পাদনা',exact:true}).click();
  await expect(page.getByLabel('ফসল (ঐচ্ছিক)')).toHaveValue('tomato');
  await expect(card).toContainText('Gazipur');
  await expect(card).not.toContainText('Dhaka');
  await page.getByLabel('ফসল (ঐচ্ছিক)').selectOption('');
  const edited = page.waitForResponse(r => r.url().endsWith('/market/products/' + listing.id) && r.request().method() === 'PATCH');
  await page.getByRole('button', {name:'পণ্য সংরক্ষণ',exact:true}).click();
  const cleared = await edited;
  expect(cleared.ok(), await cleared.text()).toBeTruthy();
  expect((await cleared.json()).commodity).toBeNull();
});

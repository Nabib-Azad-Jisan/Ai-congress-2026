import {test, expect} from '@playwright/test';

test('unavailable verification explains the disabled action beside the button', async ({page}) => {
  await page.route('**/auth/options', route => route.fulfill({json: {otp: false, signup: false, demo: true}}));
  await page.goto('/en');
  const button = page.getByRole('button', {name: 'Verification unavailable', exact: true});
  await expect(button).toBeDisabled();
  const reason = page.locator('#verification-availability');
  await expect(reason).toContainText('SMS verification is currently unavailable');
  await expect(button).toHaveAttribute('aria-describedby', 'verification-availability');
  await page.getByLabel('Receive code by').selectOption('email');
  await expect(reason).toContainText('Email verification is currently unavailable');
  await expect(page.getByRole('button', {name: 'Explore a demo farm'})).toBeEnabled();
});

test('a valid phone number can request a code when verification is configured', async ({page}) => {
  await page.route('**/auth/options', route => route.fulfill({json: {otp: true, signup: true, demo: true}}));
  await page.route('**/auth/otp/start', async route => {
    expect(route.request().postDataJSON()).toEqual({contact: '+8801712345678', purpose: 'login'});
    await route.fulfill({json: {verification_id: 'VE' + 'a'.repeat(32)}});
  });
  await page.goto('/en');
  await page.getByRole('textbox', {name: /Mobile number/}).fill('1712345678');
  await page.getByRole('button', {name: 'Send verification code'}).click();
  await expect(page.getByLabel('Verification code', {exact: true})).toBeVisible();
});

test('email-only setup selects email and does not offer SMS delivery', async ({page}) => {
  await page.route('**/auth/options', route => route.fulfill({json: {
    otp: true, signup: true, demo: true, channels: {email: true, sms: false}, default_channel: 'email',
  }}));
  await page.route('**/auth/otp/start', async route => {
    expect(route.request().postDataJSON()).toEqual({contact: 'farmer@example.test', purpose: 'login'});
    await route.fulfill({json: {verification_id: 'EM' + 'b'.repeat(32)}});
  });
  await page.goto('/en');
  await expect(page.getByLabel('Receive code by')).toHaveValue('email');
  await expect(page.locator('option[value="phone"]')).toBeDisabled();
  await page.getByLabel('Email address').fill('farmer@example.test');
  await page.getByRole('button', {name: 'Send verification code'}).click();
  await expect(page.getByLabel('Verification code', {exact: true})).toBeVisible();
  await expect(page.getByText('If your account is eligible, a code has been sent. Enter it below.')).toBeVisible();
});

test('unconfigured Gmail shows an email-specific status in Bengali', async ({page}) => {
  await page.route('**/auth/options', route => route.fulfill({json: {
    otp: false, signup: false, demo: true, channels: {email: false, sms: false}, default_channel: 'email',
  }}));
  await page.goto('/bn');
  await expect(page.getByLabel('কোড পাওয়ার মাধ্যম')).toHaveValue('email');
  await expect(page.getByRole('button', {name: 'যাচাই চালু নেই'})).toBeDisabled();
  await expect(page.locator('#verification-availability')).toContainText('ইমেইল');
});

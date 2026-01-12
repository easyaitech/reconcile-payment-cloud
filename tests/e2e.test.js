const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = process.env.BASE_URL || 'https://adventurous-enthusiasm-production.up.railway.app';

async function testFileUpload() {
  console.log('=== 测试文件上传功能 ===');
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 监听所有错误
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('Console:', msg.text());
  });

  console.log('访问页面:', BASE_URL);
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });

  // 检查 JavaScript 错误
  if (errors.length > 0) {
    console.log('❌ 页面有 JavaScript 错误:', errors[0]);
  }

  // 检查文件上传控件
  const depositInput = page.locator('input[type="file"]').nth(0);
  const withdrawInput = page.locator('input[type="file"]').nth(1);
  const submitBtn = page.locator('button[type="submit"]');

  console.log('上传充值文件...');
  await depositInput.setInputFiles('/Users/songchou/Downloads/deposit.xlsx');

  console.log('上传提款文件...');
  await withdrawInput.setInputFiles('/Users/songchou/Downloads/withdraw.xlsx');

  // 等待按钮启用
  await page.waitForTimeout(1000);
  const isDisabled = await submitBtn.isDisabled();
  console.log('提交按钮状态:', isDisabled ? '禁用' : '启用');

  // 点击添加渠道文件
  console.log('点击添加渠道文件按钮...');
  await page.locator('button:has-text("添加")').click();
  await page.waitForTimeout(500);

  // 上传渠道文件
  const channelInputs = await page.locator('input[type="file"]').count();
  console.log('当前文件输入框数量:', channelInputs);

  await browser.close();
}

async function main() {
  try {
    await testFileUpload();
  } catch (e) {
    console.error('测试失败:', e.message);
  }
}

main();

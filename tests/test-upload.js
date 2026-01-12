const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://adventurous-enthusiasm-production.up.railway.app';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 收集错误
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('Console:', msg.text());
  });

  console.log('1. 访问页面...');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });

  if (errors.length > 0) {
    console.log('❌ 页面有 JavaScript 错误:', errors[0]);
  } else {
    console.log('✅ 页面加载正常，无 JavaScript 错误');
  }

  console.log('\n2. 检查文件上传控件...');
  const fileInputs = await page.locator('input[type="file"]').count();
  console.log('   文件输入框数量:', fileInputs);

  console.log('\n3. 上传充值文件...');
  const depositInput = page.locator('input[type="file"]').nth(0);
  await depositInput.setInputFiles('/Users/songchou/Downloads/deposit.xlsx');
  console.log('   ✅ 充值文件已选择');

  console.log('\n4. 上传提款文件...');
  const withdrawInput = page.locator('input[type="file"]').nth(1);
  await withdrawInput.setInputFiles('/Users/songchou/Downloads/withdraw.xlsx');
  console.log('   ✅ 提款文件已选择');

  await page.waitForTimeout(1000);

  console.log('\n5. 检查文件列表显示...');
  // 检查是否有文件名显示
  const hasDepositFile = await page.locator('text=deposit.xlsx').count();
  const hasWithdrawFile = await page.locator('text=withdraw.xlsx').count();
  console.log('   充值文件显示:', hasDepositFile > 0 ? '✅' : '❌');
  console.log('   提款文件显示:', hasWithdrawFile > 0 ? '✅' : '❌');

  console.log('\n6. 点击添加渠道文件...');
  const addBtn = page.locator('button:has-text("添加")');
  if (await addBtn.count() > 0) {
    await addBtn.first().click();
    await page.waitForTimeout(500);
    console.log('   ✅ 已点击添加按钮');

    // 上传 BossPay 渠道文件
    const bosspayInput = page.locator('input[type="file"]').nth(2);
    await bosspayInput.setInputFiles('/Users/songchou/Downloads/bosspay.csv');
    console.log('   ✅ BossPay 文件已选择');

    // 上传 AppPay 渠道文件
    await page.waitForTimeout(500);
    const addBtn2 = page.locator('button:has-text("添加")');
    await addBtn2.nth(0).click();
    await page.waitForTimeout(500);

    const apppayInput = page.locator('input[type="file"]').nth(3);
    await apppayInput.setInputFiles('/Users/songchou/Downloads/apppay.xls');
    console.log('   ✅ AppPay 文件已选择');
  }

  console.log('\n7. 检查提交按钮状态...');
  const submitBtn = page.locator('#submitBtn');
  const isDisabled = await submitBtn.isDisabled();
  console.log('   提交按钮:', isDisabled ? '❌ 仍禁用' : '✅ 已启用');

  if (!isDisabled) {
    console.log('\n8. 点击提交按钮...');
    await submitBtn.click();
    console.log('   ✅ 已点击提交');

    // 等待结果
    console.log('\n9. 等待对账结果...');
    await page.waitForTimeout(20000);

    // 检查结果区域
    const resultText = await page.locator('body').textContent();
    if (resultText.includes('对账成功') || resultText.includes('匹配成功')) {
      console.log('   ✅ 对账成功!');
    } else if (resultText.includes('对账失败') || resultText.includes('error')) {
      console.log('   ❌ 对账失败');
    } else {
      console.log('   ⏳ 检查页面内容...');
      // 截图
      await page.screenshot({ path: '/tmp/reconcile-result.png' });
      console.log('   截图已保存到 /tmp/reconcile-result.png');
    }

    // 检查是否有异常订单
    const hasAnomalies = await page.locator('text=异常订单').count();
    const hasMissing = await page.locator('text=缺失').count();
    console.log('   显示异常订单:', hasAnomalies > 0 ? '✅' : '❌');
    console.log('   显示缺失订单:', hasMissing > 0 ? '✅' : '❌');
  }

  console.log('\n按 Ctrl+C 退出...');
  await page.waitForTimeout(30000);
  await browser.close();
})();

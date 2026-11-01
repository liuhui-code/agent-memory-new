async page => {
  const checks=[];
  const check=(name,ok)=>{if(!ok)throw new Error(name);checks.push(name);};
  const ready=()=>page.waitForFunction(()=>document.getElementById('record-list').getAttribute('aria-busy')==='false');
  await ready();
  await page.getByRole('searchbox',{name:'搜索记忆'}).fill('WORKBENCH_XSS');
  await page.waitForFunction(()=>document.getElementById('result-count').textContent==='1 条匹配');
  await page.locator('.record-open').click();
  await page.getByRole('button',{name:'归档',exact:true}).click();
  await page.locator('#dialog-submit').click();
  await page.waitForFunction(()=>document.getElementById('metric-archived').textContent==='4');await ready();
  check('fixed runtime archives controlled record',true);
  await page.locator('[data-view=archived]').click();await ready();
  await page.getByRole('searchbox',{name:'搜索记忆'}).fill('WORKBENCH_XSS');
  await page.waitForFunction(()=>document.getElementById('result-count').textContent==='1 条匹配');
  await page.locator('.record-open').click();
  await page.getByRole('button',{name:'永久删除',exact:true}).click();
  check('delete remains disabled without exact phrase',await page.locator('#dialog-submit').isDisabled());
  await page.getByRole('textbox',{name:'输入 永久删除 确认操作'}).fill('永久删除');
  await page.locator('#dialog-submit').click();
  await page.waitForFunction(()=>document.getElementById('metric-total').textContent==='2,365');await ready();
  check('fixed runtime removes only the selected generated record',true);
  const notice=await page.locator('#notice').innerText();
  check('fixed runtime returns backup path',notice.includes('before-delete-'));
  await page.getByRole('button',{name:'关闭提示',exact:true}).click();
  check('result notice can be dismissed',await page.locator('#notice').isHidden());
  await page.screenshot({path:'output/playwright/memory-review/backup-fix-delete.png',fullPage:true});
  return {passed:checks.length,checks,backup_notice:notice,final_count:2365};
}

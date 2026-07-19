/* Kenny Studio — AdSense 單一設定入口。
 *
 * 這是全站唯一需要填入真實廣告資料的檔案。
 * slot 值必須來自 AdSense 後台「廣告 → 依廣告單元」建立廣告單元後
 * 產生的 data-ad-slot 數字（例如 "1234567890"）。
 * 在取得真實 slot ID 之前請保持空字串：空值時對應版位完全不渲染，
 * 不會載入空白或錯誤的廣告框。
 */
window.KENNY_ADS = {
  client: 'ca-pub-9616816354780961',
  slots: {
    /* findtoilet/area/ 地區頁 in-content 版位 */
    area: '',
    /* findtoilet/map/ 詳情面板版位 */
    mapDetail: '',
    /* findtoilet/map/ 清單內版位 */
    mapList: '',
    /* guide 文章頁 in-article 版位 */
    guideArticle: ''
  }
};

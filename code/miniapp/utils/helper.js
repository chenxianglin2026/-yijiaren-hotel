/**
 * 伊家人酒店小程序 - 通用工具函数
 */

module.exports = {
  /**
   * 延迟指定毫秒数
   * @param {number} ms 毫秒数
   * @returns {Promise<void>}
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

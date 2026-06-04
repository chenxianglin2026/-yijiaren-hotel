/**
 * 伊家人酒店小程序 - 常量配置
 * 可配置的 API 地址、业务常量等
 */

const config = {
  // ═══════════════════════════════════════════════════
  // API 配置（按环境切换）
  // ═══════════════════════════════════════════════════

  /** API 基础地址 */
  API_BASE: 'http://192.168.43.139:8001',

  /** 开发模式：true 使用 mock 数据，false 请求真实 API */
  DEV_MODE: false,

  // ═══════════════════════════════════════════════════
  // 业务常量
  // ═══════════════════════════════════════════════════

  /** 保洁工单类型 */
  TASK_TYPES: {
    cleanup:    { label: '退房清洁',  icon: '🧹', desc: '退房后全面清洁消毒' },
    daily:      { label: '日常保洁',  icon: '🧽', desc: '客房日常打扫整理' },
    turndown:   { label: '夜床服务',  icon: '🌙', desc: '傍晚开夜床服务' },
    deep_clean: { label: '深度清洁',  icon: '✨', desc: '全面深度清洁保养' },
  },

  /** 保洁工单状态 */
  TASK_STATUS: {
    pending:     { label: '待接单',   color: '#E8A838', bg: '#FFF8E8' },
    accepted:    { label: '已接单',   color: '#5B8DEF', bg: '#EDF4FF' },
    in_progress: { label: '清洁中',   color: '#5B8DEF', bg: '#EDF4FF' },
    completed:   { label: '已完成',   color: '#6BAA75', bg: '#F0FAF0' },
    cancelled:   { label: '已取消',   color: '#B0A492', bg: '#F5F5F5' },
  },

  /** 服务请求类型 */
  SERVICE_TYPES: {
    cleaning:    { label: '呼叫保洁', icon: '🧹', desc: '需要打扫房间' },
    delivery:    { label: '客房送物', icon: '📦', desc: '毛巾/牙具/矿泉水等' },
    maintenance: { label: '维修报修', icon: '🔧', desc: '空调/热水/灯具等' },
    other:       { label: '其他服务', icon: '💁', desc: '其他客房服务' },
  },

  /** 服务请求状态 */
  SERVICE_STATUS: {
    pending:    { label: '等待处理', color: '#E8A838', bg: '#FFF8E8' },
    accepted:   { label: '已接单',   color: '#5B8DEF', bg: '#EDF4FF' },
    processing: { label: '处理中',   color: '#5B8DEF', bg: '#EDF4FF' },
    completed:  { label: '已完成',   color: '#6BAA75', bg: '#F0FAF0' },
    cancelled:  { label: '已取消',   color: '#B0A492', bg: '#F5F5F5' },
  },

  /** 服务优先级别 */
  PRIORITY: {
    normal: { label: '普通', color: '#8B7E6A' },
    urgent: { label: '紧急', color: '#C56C6C' },
  },

  // ═══════════════════════════════════════════════════
  // 存储 Key
  // ═══════════════════════════════════════════════════

  STORAGE_KEYS: {
    TOKEN: 'token',
    USER_INFO: 'userInfo',
    CURRENT_STORE: 'currentStore',
    LOCATION: 'location',
  },

  // ═══════════════════════════════════════════════════
  // 分页默认值
  // ═══════════════════════════════════════════════════

  PAGE_SIZE: 20,
  PAGE_SIZE_SMALL: 10,
}

module.exports = config

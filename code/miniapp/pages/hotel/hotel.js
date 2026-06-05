const app = getApp()
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    storeId: '',
    store: null,
    loading: true,
    isFavorite: false,
    filteredRooms: []
  },

  onLoad(options) {
    const storeId = options.id || '1'
    this.setData({ storeId })
    this.loadStoreDetail(storeId)
    this.checkFavoriteStatus(storeId)
  },

  onShow() {
    // 检查当前门店是否匹配
    const currentStore = app.globalData.currentStore
    if (currentStore && this.data.store) {
      this.setData({ store: { ...this.data.store, ...currentStore } })
    }
  },

  // ========== 加载门店详情 ==========
  loadStoreDetail(storeId) {
    const that = this
    this.setData({ loading: true })

    api.get(`/api/hotels/${storeId}`)
      .then(store => {
        // 确保必要字段存在
        const normalized = {
          ...store,
          type: store.type || '精品酒店',
          images: store.images && store.images.length > 0
            ? store.images
            : ['banner-1', 'banner-2', 'banner-3', 'banner-4'],
          facilities: store.facilities || [],
          rooms: store.rooms || [],
          nearby: store.nearby || [],
          highlights: store.highlights || [],
          rating: store.rating || 0,
          reviewCount: store.review_count || 0,
          hasParking: store.has_parking !== undefined ? store.has_parking : true
        }
        that.setData({ store: normalized, loading: false })
      })
      .catch(err => {
        if (C.DEV_MODE) console.error('[Hotel] 加载门店详情失败:', err)
        that.setData({ loading: false })
        wx.showToast({ title: '加载失败，请重试', icon: 'none' })
      })
  },

  // ========== 收藏状态 ==========
  checkFavoriteStatus(storeId) {
    const favorites = wx.getStorageSync('favorites') || []
    const isFavorite = favorites.includes(parseInt(storeId))
    this.setData({ isFavorite })
  },

  // ========== 图片预览 ==========
  onPreviewImage(e) {
    const { index } = e.currentTarget.dataset
    const urls = this.data.store.images.map(img => `/images/${img}.png`)
    wx.previewImage({ urls, current: urls[index] || urls[0] })
  },

  // ========== 收藏切换 ==========
  onFavorite() {
    const { store, isFavorite } = this.data
    let favorites = wx.getStorageSync('favorites') || []

    if (isFavorite) {
      favorites = favorites.filter(id => id !== store.id)
      wx.showToast({ title: '已取消收藏', icon: 'none' })
    } else {
      favorites.push(store.id)
      wx.showToast({ title: '已收藏', icon: 'success' })
    }

    wx.setStorageSync('favorites', favorites)
    this.setData({ isFavorite: !isFavorite })
  },

  // ========== 分享 ==========
  onShare() {
    wx.showToast({ title: '分享功能开发中', icon: 'none' })
  },

  // ========== 导航到门店 ==========
  onOpenLocation() {
    const { store } = this.data
    wx.openLocation({
      latitude: store.lat,
      longitude: store.lng,
      name: store.name,
      address: store.address,
      scale: 16
    })
  },

  // ========== 拨打电话 ==========
  onCallStore() {
    const { store } = this.data
    wx.makePhoneCall({
      phoneNumber: store.phone
    })
  },

  // ========== 房型导航 ==========
  onRoomTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/room/room?id=${id}` })
  },

  onBookTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/booking/booking?roomId=${id}` })
  },

  // ========== 预订房间 ==========
  onBookRoom() {
    const { store } = this.data
    if (store.rooms.length > 0) {
      wx.navigateTo({ url: `/pages/booking/booking?roomId=${store.rooms[0].id}` })
    } else {
      wx.showToast({ title: '暂无可预订房型', icon: 'none' })
    }
  },

  // ========== 分享配置 ==========
  onShareAppMessage() {
    const { store } = this.data
    return {
      title: store ? `${store.name} - 伊家人酒店` : '伊家人酒店',
      path: `/pages/hotel/hotel?id=${this.data.storeId}`,
      imageUrl: '/images/share-hotel.png'
    }
  }
})

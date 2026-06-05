/**
 * 伊家人小程序 - 首页
 * 接入真实后端API：酒店列表 / 房型列表 / 仪表盘统计
 */
const api = require('../../utils/api')
const C = require('../../utils/const')
const app = getApp()

Page({
  data: {
    // 当前城市
    city: '定位中...',
    // 当前定位
    location: null,
    // 搜索关键词
    searchKey: '',
    // 筛选条件
    filters: {
      priceRange: 'all',    // all | under300 | 300to500 | 500to800 | above800
      roomType: 'all',      // all | 大床房 | 双床房 | 套房 | 家庭房 | 单人间
      hasWindow: false,
      breakfast: false
    },
    showFilters: false,
    // 原始房型列表（用于筛选）
    _allRooms: [],
    // 房型列表（展示用）
    roomList: [],
    // 筛选后的列表
    filteredRooms: null,
    // 酒店列表
    hotelList: [],
    // 当前选中的酒店
    currentHotel: null,
    // 酒店ID（从app.globalData获取或默认1）
    hotelId: 1,
    // Banner轮播
    banners: [],
    // 加载状态
    loading: true,
    loadingMore: false,
    hasMore: true,
    // 品牌特色
    features: [
      { icon: '🏨', label: '品质酒店', desc: '精选房源' },
      { icon: '🛏️', label: '舒适床品', desc: '星级睡眠' },
      { icon: '🧹', label: '一客一换', desc: '卫生保障' },
      { icon: '🔑', label: '智能门锁', desc: '自助入住' },
      { icon: '🅿️', label: '免费停车', desc: '出行无忧' },
      { icon: '🍳', label: '营养早餐', desc: '元气满满' }
    ]
  },

  onLoad() {
    this.getLocation()
    this.loadBanners()
    this.loadHotels()
  },

  onShow() {
    // 如果从其他页面切换回来，检查门店是否变化
    const store = app.globalData.currentStore
    if (store && this.data.hotelId !== store.id) {
      this.setData({
        hotelId: store.id,
        currentHotel: store
      })
      this.loadRooms()
    }
  },

  onPullDownRefresh() {
    Promise.all([
      this.loadHotels(),
      this.loadRooms()
    ]).then(() => wx.stopPullDownRefresh())
  },

  // ========== LBS 定位 ==========
  getLocation() {
    const that = this
    wx.getLocation({
      type: 'gcj02',
      success(res) {
        app.globalData.location = {
          lat: res.latitude,
          lng: res.longitude
        }
        that.reverseGeocode(res.latitude, res.longitude)
      },
      fail() {
        // 定位失败使用默认位置
        that.setData({ city: '全国' })
        that.loadRooms()
      }
    })
  },

  reverseGeocode(lat, lng) {
    const that = this
    // TODO: 配置腾讯地图key后启用逆地理编码
    // 目前直接根据定位加载数据
    this.setData({ city: '杭州' })
    app.globalData.location.city = '杭州'
    this.loadRooms()
  },

  // ========== 加载Banner ==========
  loadBanners() {
    // 可接入 /api/dashboard/promotions 或配置文件
    this.setData({
      banners: [
        {
          id: 1,
          image: '/images/banner-1.png',
          title: '新店开业 · 首单立减50元',
          link: ''
        },
        {
          id: 2,
          image: '/images/banner-2.png',
          title: '会员专享 · 周末8折',
          link: ''
        },
        {
          id: 3,
          image: '/images/banner-3.png',
          title: '智能入住 · 无需前台',
          link: ''
        }
      ]
    })
  },

  // ========== 加载酒店列表 ==========
  async loadHotels() {
    try {
      const res = await api.get('/api/hotels', {
        city: this.data.city === '全国' ? undefined : this.data.city,
        page_size: 50
      })
      const hotels = res.items || []
      this.setData({ hotelList: hotels })

      // 如果app.globalData中有currentStore，使用它
      const store = app.globalData.currentStore
      if (store && store.id) {
        this.setData({
          hotelId: store.id,
          currentHotel: store
        })
      } else if (hotels.length > 0) {
        // 默认选第一个酒店
        const firstHotel = hotels[0]
        this.setData({
          hotelId: firstHotel.id,
          currentHotel: firstHotel
        })
        app.switchStore(firstHotel)
      }
    } catch (err) {
      if (C.DEV_MODE) console.error('[首页] 加载酒店列表失败:', err)
    }
  },

  // ========== 加载房型（从真实API） ==========
  async loadRooms() {
    const that = this
    this.setData({ loading: true })

    try {
      const hotelId = this.data.hotelId
      if (!hotelId) {
        // 没有酒店ID，尝试先加载酒店列表
        await this.loadHotels()
        if (!this.data.hotelId) {
          this.setData({ loading: false })
          return
        }
      }

      const currentHotelId = this.data.hotelId

      // 调用真实API: GET /api/hotels/{hotel_id}/rooms
      const rooms = await api.get(`/api/hotels/${currentHotelId}/rooms`)

      // 将后端数据转换为小程序展示格式
      const roomList = rooms.map(room => ({
        id: room.id,
        hotel_id: room.hotel_id,
        name: room.name,
        image: room.images || '/images/room-default.png',
        type: room.room_type,
        area: `${room.area || 25}m²`,
        bed: room.bed_type || '1.8m大床',
        window: room.has_window,
        breakfast: room.has_bathtub,  // 有浴缸通常也含早
        wifi: room.has_wifi,
        floor: '详情见描述',
        maxGuests: room.max_guests,
        originalPrice: Math.round(room.price * 1.2),
        price: room.price,
        tags: room.has_bathtub ? ['浴缸'] : [],
        available: room.available_count,
        description: room.description || ''
      }))

      that.setData({
        _allRooms: roomList,
        roomList: roomList,
        loading: false,
        filteredRooms: null
      })
    } catch (err) {
      if (C.DEV_MODE) console.error('[首页] 加载房型失败:', err)
      that.setData({
        loading: false,
        roomList: []
      })
      wx.showToast({ title: '加载失败，下拉刷新重试', icon: 'none' })
    }
  },

  // ========== 切换酒店 ==========
  async onHotelChange(e) {
    const hotelId = e.currentTarget.dataset.id
    const hotel = this.data.hotelList.find(h => h.id === hotelId)
    if (hotel) {
      this.setData({
        hotelId: hotel.id,
        currentHotel: hotel
      })
      app.switchStore(hotel)
      await this.loadRooms()
    }
  },

  // ========== 搜索 ==========
  onSearchInput(e) {
    this.setData({ searchKey: e.detail.value })
  },

  onSearch() {
    const key = this.data.searchKey.trim()
    if (!key) {
      this.setData({ filteredRooms: null })
      return
    }
    // 本地过滤
    const source = this.data._allRooms
    const filtered = source.filter(item =>
      item.name.includes(key) ||
      (item.description && item.description.includes(key)) ||
      (item.type && item.type.includes(key))
    )
    this.setData({ filteredRooms: filtered })
  },

  onSearchClear() {
    this.setData({ searchKey: '', filteredRooms: null })
  },

  // ========== 筛选 ==========
  toggleFilters() {
    this.setData({ showFilters: !this.data.showFilters })
  },

  onFilterChange(e) {
    const { field, value } = e.currentTarget.dataset
    const filters = { ...this.data.filters }
    if (field === 'priceRange' || field === 'roomType') {
      filters[field] = value
    } else {
      filters[field] = !filters[field]
    }
    this.setData({ filters })
    this.applyFilters()
  },

  applyFilters() {
    const { filters } = this.data
    const source = this.data._allRooms
    let rooms = [...source]

    // 房型筛选
    if (filters.roomType !== 'all') {
      rooms = rooms.filter(r => r.type === filters.roomType)
    }
    // 价格筛选
    if (filters.priceRange !== 'all') {
      rooms = rooms.filter(r => {
        switch (filters.priceRange) {
          case 'under300': return r.price < 300
          case '300to500': return r.price >= 300 && r.price < 500
          case '500to800': return r.price >= 500 && r.price < 800
          case 'above800': return r.price >= 800
          default: return true
        }
      })
    }
    // 有窗
    if (filters.hasWindow) {
      rooms = rooms.filter(r => r.window)
    }
    // 含早（用有浴缸近似）
    if (filters.breakfast) {
      rooms = rooms.filter(r => r.breakfast)
    }
    this.setData({ filteredRooms: rooms })
  },

  resetFilters() {
    this.setData({
      filters: {
        priceRange: 'all',
        roomType: 'all',
        hasWindow: false,
        breakfast: false
      },
      filteredRooms: null
    })
  },

  // ========== 导航 ==========
  onRoomTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/room/room?id=${id}` })
  },

  onBookTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/booking/booking?roomId=${id}` })
  },

  // 切换门店（保留兼容）
  onSwitchStore() {
    const hotels = this.data.hotelList
    if (hotels.length === 0) {
      wx.showToast({ title: '暂无门店', icon: 'none' })
      return
    }
    const itemList = hotels.map(h => h.name)
    const that = this
    wx.showActionSheet({
      itemList,
      success(res) {
        const hotel = hotels[res.tapIndex]
        that.setData({
          hotelId: hotel.id,
          currentHotel: hotel
        })
        app.switchStore(hotel)
        that.loadRooms()
      }
    })
  }
})

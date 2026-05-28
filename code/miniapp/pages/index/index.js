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
      roomType: 'all',      // all | single | double | suite | family
      hasWindow: false,
      breakfast: false
    },
    showFilters: false,
    // 房型列表
    roomList: [],
    // 门店信息
    storeInfo: null,
    // Banner轮播
    banners: [],
    // 加载状态
    loading: true,
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
  },

  onShow() {
    const store = app.globalData.currentStore
    if (store) {
      this.setData({ storeInfo: store })
    }
  },

  onPullDownRefresh() {
    this.loadRooms().then(() => wx.stopPullDownRefresh())
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
        that.setData({ city: '杭州' })
        that.loadRooms()
      }
    })
  },

  reverseGeocode(lat, lng) {
    const that = this
    wx.request({
      url: `https://apis.map.qq.com/ws/geocoder/v1/?location=${lat},${lng}&key=YOUR_KEY`,
      success(res) {
        if (res.data.status === 0) {
          const city = res.data.result.address_component.city || '杭州'
          that.setData({ city })
          app.globalData.location.city = city
        } else {
          that.setData({ city: '杭州' })
        }
        that.loadRooms()
      },
      fail() {
        that.setData({ city: '杭州' })
        that.loadRooms()
      }
    })
  },

  // ========== 加载Banner ==========
  loadBanners() {
    // 模拟数据 - 实际从接口获取
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

  // ========== 加载房型 ==========
  loadRooms() {
    const that = this
    this.setData({ loading: true })

    // TODO: 替换为真实API
    // app.request({ url: '/rooms', data: { storeId: app.globalData.currentStore.id } })

    // 模拟酒店真实房型数据
    const mockRooms = [
      {
        id: 101,
        name: '雅致大床房',
        image: '/images/room-double.png',
        type: 'double',
        area: '28㎡',
        bed: '1.8m大床',
        window: true,
        breakfast: true,
        wifi: true,
        floor: '3-8层',
        maxGuests: 2,
        originalPrice: 368,
        price: 298,
        tags: ['限量特惠', '含双早'],
        available: 5,
        description: '简约雅致设计，配备金可儿床垫，干湿分离卫浴'
      },
      {
        id: 102,
        name: '豪华双床房',
        image: '/images/room-twin.png',
        type: 'double',
        area: '35㎡',
        bed: '1.35m双床',
        window: true,
        breakfast: true,
        wifi: true,
        floor: '5-12层',
        maxGuests: 2,
        originalPrice: 458,
        price: 368,
        tags: ['含双早', '高层景观'],
        available: 8,
        description: '宽敞双床布局，适合商务出行或亲友同住'
      },
      {
        id: 201,
        name: '尊享套房',
        image: '/images/room-suite.png',
        type: 'suite',
        area: '55㎡',
        bed: '2.0m大床',
        window: true,
        breakfast: true,
        wifi: true,
        floor: '15-20层',
        maxGuests: 2,
        originalPrice: 788,
        price: 598,
        tags: ['独立客厅', '浴缸', '城市景观'],
        available: 3,
        description: '一室一厅格局，独立会客厅，全景落地窗尽揽城市风光'
      },
      {
        id: 301,
        name: '亲子家庭房',
        image: '/images/room-family.png',
        type: 'family',
        area: '42㎡',
        bed: '1.8m大床+1.2m小床',
        window: true,
        breakfast: true,
        wifi: true,
        floor: '6-10层',
        maxGuests: 3,
        originalPrice: 528,
        price: 428,
        tags: ['儿童主题', '含三早'],
        available: 4,
        description: '童趣主题布置，配备儿童用品、安全护栏，亲子出行首选'
      },
      {
        id: 103,
        name: '舒适单人间',
        image: '/images/room-single.png',
        type: 'single',
        area: '22㎡',
        bed: '1.5m大床',
        window: true,
        breakfast: false,
        wifi: true,
        floor: '2-5层',
        maxGuests: 1,
        originalPrice: 258,
        price: 198,
        tags: ['经济实惠'],
        available: 6,
        description: '精致小巧空间，功能齐全，商务出差高性价比之选'
      },
      {
        id: 202,
        name: '行政景观套房',
        image: '/images/room-executive.png',
        type: 'suite',
        area: '65㎡',
        bed: '2.0m大床',
        window: true,
        breakfast: true,
        wifi: true,
        floor: '18-22层',
        maxGuests: 2,
        originalPrice: 988,
        price: 738,
        tags: ['行政酒廊', '管家服务', '全景视野'],
        available: 2,
        description: '行政楼层专属礼遇，独立办公区，180°全景落地窗'
      }
    ]

    // 模拟网络延迟
    setTimeout(() => {
      that.setData({
        roomList: mockRooms,
        loading: false
      })
    }, 600)
  },

  // ========== 搜索 ==========
  onSearchInput(e) {
    this.setData({ searchKey: e.detail.value })
  },

  onSearch() {
    const key = this.data.searchKey.trim()
    if (!key) {
      this.loadRooms()
      return
    }
    // 本地过滤
    const filtered = this.data.roomList.filter(item =>
      item.name.includes(key) || item.description.includes(key)
    )
    this.setData({ roomList: filtered })
  },

  onSearchClear() {
    this.setData({ searchKey: '' })
    this.loadRooms()
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
    const { filters, roomList } = this.data
    // 重新加载所有房间再做筛选
    let rooms = roomList

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
    // 含早
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

  // 切换门店
  onSwitchStore() {
    wx.showActionSheet({
      itemList: ['伊家人酒店·西湖店', '伊家人酒店·钱江店', '伊家人酒店·西溪店'],
      success(res) {
        const stores = [
          { id: 1, name: '伊家人酒店·西湖店', address: '杭州市西湖区龙井路88号', lat: 30.2375, lng: 120.1398, phone: '0571-88886666' },
          { id: 2, name: '伊家人酒店·钱江店', address: '杭州市上城区钱江路168号', lat: 30.2448, lng: 120.2120, phone: '0571-88887777' },
          { id: 3, name: '伊家人酒店·西溪店', address: '杭州市余杭区文二西路952号', lat: 30.2713, lng: 120.0581, phone: '0571-88888888' }
        ]
        app.switchStore(stores[res.tapIndex])
      }
    })
  }
})

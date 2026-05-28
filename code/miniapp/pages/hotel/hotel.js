const app = getApp()
const api = require('../../utils/api')

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

    // 门店模拟数据
    const stores = {
      1: {
        id: 1,
        name: '伊家人酒店·西湖店',
        type: '精品酒店',
        address: '杭州市西湖区龙井路88号',
        phone: '0571-88886666',
        lat: 30.2375,
        lng: 120.1398,
        rating: 4.8,
        reviewCount: 1280,
        hasParking: true,
        description: '坐落于西湖畔龙井路，步行五分钟即可抵达西湖十景之一的"曲院风荷"。酒店以新中式设计风格为主调，融合江南园林元素，营造静谧雅致的居住氛围。全店配备智能门锁系统，支持自助入住、刷脸开门，为您提供便捷高效的入住体验。',
        highlights: [
          '步行5分钟至西湖 · 尽览湖光山色',
          '全智能门锁 · 自助入住 · 刷脸开门',
          '金可儿床垫 · 300支纯棉床品 · 星级睡眠',
          '每日新鲜早餐 · 本地特色与西式结合',
          '免费停车场 · 可停50+车辆',
          '24小时管家服务 · 行李寄存 · 叫醒服务'
        ],
        facilities: [
          { icon: '🅿️', label: '免费停车' },
          { icon: '📶', label: '免费WiFi' },
          { icon: '🧳', label: '行李寄存' },
          { icon: '🧹', label: '每日清洁' },
          { icon: '🔑', label: '智能门锁' },
          { icon: '📺', label: '智能电视' },
          { icon: '❄️', label: '中央空调' },
          { icon: '🔒', label: '保险箱' },
          { icon: '🛗', label: '电梯' },
          { icon: '♿', label: '无障碍通道' },
          { icon: '👶', label: '婴儿床' },
          { icon: '🐾', label: '可带宠物' }
        ],
        nearby: [
          { icon: '🏞️', name: '西湖风景区', distance: '500m', type: '景点' },
          { icon: '🛍️', name: '湖滨银泰in77', distance: '2.1km', type: '购物' },
          { icon: '🍜', name: '知味观总店', distance: '1.8km', type: '美食' },
          { icon: '🚇', name: '龙翔桥地铁站', distance: '1.5km', type: '交通' },
          { icon: '🏥', name: '浙江大学附属第一医院', distance: '2.5km', type: '医院' }
        ],
        images: ['banner-1', 'banner-2', 'banner-3', 'banner-4'],
        rooms: [
          {
            id: 101, name: '雅致大床房', type: 'double', area: '28㎡', bed: '1.8m大床',
            window: true, breakfast: true, originalPrice: 368, price: 298,
            tags: ['限量特惠', '含双早'], available: 5,
            description: '简约雅致设计，配备金可儿床垫，干湿分离卫浴'
          },
          {
            id: 102, name: '豪华双床房', type: 'double', area: '35㎡', bed: '1.35m双床',
            window: true, breakfast: true, originalPrice: 458, price: 368,
            tags: ['含双早', '高层景观'], available: 8,
            description: '宽敞双床布局，适合商务出行或亲友同住'
          },
          {
            id: 201, name: '尊享套房', type: 'suite', area: '55㎡', bed: '2.0m大床',
            window: true, breakfast: true, originalPrice: 788, price: 598,
            tags: ['独立客厅', '浴缸', '城市景观'], available: 3,
            description: '一室一厅格局，独立会客厅，全景落地窗尽揽城市风光'
          },
          {
            id: 301, name: '亲子家庭房', type: 'family', area: '42㎡', bed: '1.8m大床+1.2m小床',
            window: true, breakfast: true, originalPrice: 528, price: 428,
            tags: ['儿童主题', '含三早'], available: 4,
            description: '童趣主题布置，配备儿童用品、安全护栏，亲子出行首选'
          },
          {
            id: 103, name: '舒适单人间', type: 'single', area: '22㎡', bed: '1.5m大床',
            window: true, breakfast: false, originalPrice: 258, price: 198,
            tags: ['经济实惠'], available: 6,
            description: '精致小巧空间，功能齐全，商务出差高性价比之选'
          }
        ]
      },
      2: {
        id: 2,
        name: '伊家人酒店·钱江店',
        type: '商务酒店',
        address: '杭州市上城区钱江路168号',
        phone: '0571-88887777',
        lat: 30.2448,
        lng: 120.2120,
        rating: 4.7,
        reviewCount: 856,
        hasParking: true,
        description: '地处钱江新城CBD核心区域，毗邻市民中心和杭州大剧院。酒店以现代商务风格为主，配备高速网络和智能办公设备，是商务出行的理想之选。周边餐饮购物配套齐全，出行便利。',
        highlights: [
          '钱江新城CBD核心 · 商务出行首选',
          '高速WiFi · 智能办公桌 · 人体工学椅',
          '金可儿床垫 · 隔音玻璃 · 深度睡眠',
          '每日自助早餐 · 中西式60+品种',
          '免费停车 · 会议室 · 商务中心',
          '健身房 · 洗衣服务 · 24小时前台'
        ],
        facilities: [
          { icon: '🅿️', label: '免费停车' },
          { icon: '📶', label: '高速WiFi' },
          { icon: '🏋️', label: '健身房' },
          { icon: '🧹', label: '每日清洁' },
          { icon: '🔑', label: '智能门锁' },
          { icon: '💼', label: '商务中心' },
          { icon: '📋', label: '会议室' },
          { icon: '👔', label: '洗衣服务' }
        ],
        nearby: [
          { icon: '🏛️', name: '杭州大剧院', distance: '800m', type: '文化' },
          { icon: '🛍️', name: '万象城', distance: '1.2km', type: '购物' },
          { icon: '🏢', name: '市民中心', distance: '600m', type: '政务' },
          { icon: '🚇', name: '市民中心地铁站', distance: '400m', type: '交通' }
        ],
        images: ['banner-1', 'banner-2', 'banner-3'],
        rooms: [
          {
            id: 101, name: '商务大床房', type: 'double', area: '30㎡', bed: '1.8m大床',
            window: true, breakfast: true, originalPrice: 398, price: 328,
            tags: ['商务优选', '含早餐'], available: 10,
            description: '现代商务风格，配备智能办公桌和人体工学椅'
          },
          {
            id: 102, name: '商务双床房', type: 'double', area: '35㎡', bed: '1.35m双床',
            window: true, breakfast: true, originalPrice: 458, price: 368,
            tags: ['含双早', '高层景观'], available: 6,
            description: '宽敞双床，一览钱塘江夜景'
          },
          {
            id: 202, name: '行政套房', type: 'suite', area: '60㎡', bed: '2.0m大床',
            window: true, breakfast: true, originalPrice: 888, price: 698,
            tags: ['行政酒廊', '江景视野', '管家服务'], available: 2,
            description: '行政楼层专属礼遇，180°钱塘江江景'
          }
        ]
      },
      3: {
        id: 3,
        name: '伊家人酒店·西溪店',
        type: '度假酒店',
        address: '杭州市余杭区文二西路952号',
        phone: '0571-88888888',
        lat: 30.2713,
        lng: 120.0581,
        rating: 4.9,
        reviewCount: 632,
        hasParking: true,
        description: '隐匿于西溪湿地畔的静谧度假酒店，坐拥湿地生态景观。酒店以自然生态设计理念，大量使用原木和石材元素，打造返璞归真的度假空间。每间客房均可欣赏湿地美景，让您在自然怀抱中放松身心。',
        highlights: [
          '西溪湿地畔 · 推窗即景 · 天然氧吧',
          '原木设计 · 石材元素 · 返璞归真',
          '席梦思床垫 · 有机棉床品 · 深度睡眠',
          '湿地景观餐厅 · 本地有机食材',
          '免费停车 · 自行车租赁 · 湿地导览',
          '儿童乐园 · 宠物友好 · 棋牌室'
        ],
        facilities: [
          { icon: '🅿️', label: '免费停车' },
          { icon: '📶', label: '免费WiFi' },
          { icon: '🚲', label: '自行车租赁' },
          { icon: '🌿', label: '湿地花园' },
          { icon: '🍽️', label: '景观餐厅' },
          { icon: '🧒', label: '儿童乐园' },
          { icon: '🐾', label: '宠物友好' },
          { icon: '🀄', label: '棋牌室' }
        ],
        nearby: [
          { icon: '🌿', name: '西溪国家湿地公园', distance: '200m', type: '景点' },
          { icon: '🛍️', name: '西溪印象城', distance: '1.5km', type: '购物' },
          { icon: '🍜', name: '西溪慢生活街区', distance: '300m', type: '美食' },
          { icon: '🏛️', name: '中国湿地博物馆', distance: '800m', type: '文化' },
          { icon: '🚇', name: '西溪湿地南地铁站', distance: '1.2km', type: '交通' }
        ],
        images: ['banner-1', 'banner-2', 'banner-3', 'banner-4'],
        rooms: [
          {
            id: 101, name: '园景大床房', type: 'double', area: '32㎡', bed: '1.8m大床',
            window: true, breakfast: true, originalPrice: 428, price: 358,
            tags: ['湿地景观', '含双早'], available: 7,
            description: '落地窗直面湿地花园，清晨被鸟鸣唤醒'
          },
          {
            id: 201, name: '湿地观景套房', type: 'suite', area: '58㎡', bed: '2.0m大床',
            window: true, breakfast: true, originalPrice: 858, price: 658,
            tags: ['全景湿地', '私享阳台', '浴缸'], available: 2,
            description: '独立观景阳台，180°饱览西溪湿地风光'
          },
          {
            id: 301, name: '亲子湿地房', type: 'family', area: '45㎡', bed: '1.8m大床+1.2m小床',
            window: true, breakfast: true, originalPrice: 588, price: 468,
            tags: ['亲子主题', '含三早', '儿童用品'], available: 3,
            description: '亲子露营主题，配备帐篷小床和儿童玩具'
          }
        ]
      }
    }

    // 模拟网络延迟
    setTimeout(() => {
      const store = stores[storeId] || stores[1]
      that.setData({ store, loading: false })
    }, 400)

    // TODO: 接入真实API
    // api.get(`/stores/${storeId}`).then(store => {
    //   that.setData({ store, loading: false })
    // }).catch(() => {
    //   that.setData({ loading: false })
    // })
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

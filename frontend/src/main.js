import Vue from 'vue'
import App from './App'
import router from './router'
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
import axios from 'axios'

Vue.config.productionTip = false

const apiBaseUrl = process.env.VUE_APP_BASEURL || 'http://127.0.0.1:5000/'

axios.defaults.baseURL = apiBaseUrl
axios.defaults.withCredentials = false

Vue.prototype.$http = axios
Vue.prototype.$apiBaseUrl = apiBaseUrl

Vue.use(ElementUI);

new Vue({
  el: '#app',
  router,
  components: { App },
  template: '<App/>'
})

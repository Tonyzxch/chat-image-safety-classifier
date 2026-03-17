import Vue from 'vue'
import Router from 'vue-router'

import Predict from '@/components/Predict'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'Predict',
      component: Predict
    }
  ]
})

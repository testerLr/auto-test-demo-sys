<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { resetData } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const auth = useAuthStore()
const cart = useCartStore()
const router = useRouter()

onMounted(() => {
  void cart.refresh()
})

watch(
  () => auth.token,
  () => {
    void cart.refresh()
  },
)

async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '将清空所有订单、购物车与新增商品，并恢复种子数据，确定继续？',
      '重置测试数据',
      { type: 'warning', confirmButtonText: '重置', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const result = await resetData()
  await cart.refresh()
  ElMessage.success(
    `数据已重置：用户 ${result.users} 个、分类 ${result.categories} 个、商品 ${result.products} 个`,
  )
}

function handleLogout() {
  auth.logout()
  cart.reset()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div>
    <header class="shop-header">
      <div class="shop-header__inner">
        <router-link to="/" class="brand">🛍 Auto Test Demo 商城</router-link>

        <nav class="shop-header__nav">
          <el-menu mode="horizontal" :ellipsis="false" router :default-active="$route.path">
            <el-menu-item index="/">商品</el-menu-item>
            <el-menu-item v-if="auth.isLoggedIn" index="/orders">
              我的订单
            </el-menu-item>
            <el-menu-item v-if="auth.isAdmin" index="/admin/products">
              商品管理
            </el-menu-item>
          </el-menu>
        </nav>

        <div class="shop-header__actions">
          <el-button link type="info" @click="handleReset">重置测试数据</el-button>

          <router-link to="/cart" class="cart-link">
            <el-badge :value="cart.count" :hidden="cart.count === 0" :max="99">
              <el-icon :size="20"><ShoppingCart /></el-icon>
            </el-badge>
            <span>购物车</span>
          </router-link>

          <template v-if="auth.isLoggedIn">
            <el-dropdown @command="(cmd: string) => cmd === 'logout' && handleLogout()">
              <span class="el-dropdown-link" style="cursor: pointer">
                {{ auth.user?.nickname || auth.user?.username }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item disabled>
                    {{ auth.user?.username }}
                    {{ auth.isAdmin ? '（管理员）' : '' }}
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button size="small" @click="router.push('/login')">登录</el-button>
            <el-button size="small" type="primary" @click="router.push('/register')">
              注册
            </el-button>
          </template>
        </div>
      </div>
    </header>

    <main>
      <router-view />
    </main>

    <footer class="shop-footer">
      Auto Test Demo System · 支付为内置模拟网关 · 数据可通过「重置测试数据」恢复
    </footer>
  </div>
</template>

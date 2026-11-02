<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { resetData } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const auth = useAuthStore()
const cart = useCartStore()
const router = useRouter()
const route = useRoute()

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
  <el-container class="admin-layout">
    <el-aside width="200px" class="admin-aside">
      <div class="admin-brand">⚙ 管理后台</div>
      <el-menu
        :default-active="route.path"
        router
        background-color="#1f2d3d"
        text-color="#bfcbd9"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/admin/products">
          <el-icon><Goods /></el-icon>
          <span>商品管理</span>
        </el-menu-item>
        <el-menu-item index="/">
          <el-icon><Back /></el-icon>
          <span>返回商城</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <span class="admin-header__title">商品管理</span>
        <div class="admin-header__actions">
          <el-button link type="danger" @click="handleReset">重置测试数据</el-button>
          <el-dropdown @command="(cmd: string) => cmd === 'logout' && handleLogout()">
            <span style="cursor: pointer">
              {{ auth.user?.nickname || auth.user?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>管理员</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

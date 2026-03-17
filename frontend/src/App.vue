<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: "App",
};
</script>

<style>
body {
  margin: 0;
  font-family: "Segoe UI", "PingFang SC", sans-serif;
  background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
  color: #17202a;
}

#app {
  min-height: 100vh;
}
</style>

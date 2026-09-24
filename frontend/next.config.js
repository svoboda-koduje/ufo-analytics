/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  experimental: { useTypeScriptCli: false, workerThreads: true, webpackBuildWorker: false },
};

module.exports = nextConfig;

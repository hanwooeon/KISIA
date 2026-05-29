import electron from 'electron'
console.log('[DEBUG] typeof electron:', typeof electron)
console.log('[DEBUG] electron value:', JSON.stringify(electron)?.slice(0, 120))
const { app, BrowserWindow, shell, ipcMain } = (typeof electron === 'object' && electron !== null) ? electron : {}
console.log('[DEBUG] app:', typeof app, '| ipcMain:', typeof ipcMain)
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname  = dirname(__filename)
const isDev      = process.env.NODE_ENV === 'development'
let win

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    frame: false,
    backgroundColor: '#0F172A',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: join(__dirname, 'preload.cjs'),
    },
    show: false,
  })

  if (isDev) {
    win.loadURL('http://localhost:5175')
  } else {
    win.loadFile(join(__dirname, '../dist/index.html'))
  }

  win.once('ready-to-show', () => win.show())

  win.on('maximize',   () => win.webContents.send('maximize-change', true))
  win.on('unmaximize', () => win.webContents.send('maximize-change', false))

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

ipcMain.on('window-minimize', () => win?.minimize())
ipcMain.on('window-maximize', () => win?.isMaximized() ? win.unmaximize() : win.maximize())
ipcMain.on('window-close',    () => win?.close())

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

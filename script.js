/**
 * アイコンリサイザー - フロントエンドJavaScript
 * ドラッグ&ドロップ、プリセット選択、非同期アップロードを処理
 */

class IconResizer {
    constructor() {
        this.selectedFile = null;
        this.selectedPreset = null;
        this.presets = {};
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadPresets();
    }
    
    initializeElements() {
        // DOM要素を取得
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.previewArea = document.getElementById('previewArea');
        this.previewImage = document.getElementById('previewImage');
        this.imageInfo = document.getElementById('imageInfo');
        this.clearBtn = document.getElementById('clearBtn');
        this.presetGrid = document.getElementById('presetGrid');
        this.customSizes = document.getElementById('customSizes');
        this.customBtn = document.getElementById('customBtn');
        this.processing = document.getElementById('processing');
        this.errorMessage = document.getElementById('errorMessage');
    }
    
    setupEventListeners() {
        // ファイルアップロード関連
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // ドラッグ&ドロップ
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // プレビュークリア
        this.clearBtn.addEventListener('click', () => this.clearPreview());
        
        // カスタムサイズ処理
        this.customBtn.addEventListener('click', () => this.handleCustomResize());
        
        // カスタムサイズ入力のEnterキー対応
        this.customSizes.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleCustomResize();
            }
        });
    }
    
    async loadPresets() {
        try {
            const response = await fetch('/api/presets');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.presets = await response.json();
            this.renderPresets();
        } catch (error) {
            console.error('プリセットの読み込みに失敗しました:', error);
            this.showError('プリセットの読み込みに失敗しました');
        }
    }
    
    renderPresets() {
        this.presetGrid.innerHTML = '';
        
        Object.entries(this.presets).forEach(([id, preset]) => {
            const card = this.createPresetCard(id, preset);
            this.presetGrid.appendChild(card);
        });
    }
    
    createPresetCard(id, preset) {
        const card = document.createElement('div');
        card.className = 'preset-card';
        card.dataset.presetId = id;
        
        // プリセットアイコンを決定
        const icon = this.getPresetIcon(id);
        
        card.innerHTML = `
            <div class="preset-icon">${icon}</div>
            <div class="preset-name">${preset.name}</div>
            <div class="preset-sizes">${preset.sizes.join(' × ')}px</div>
            <div class="preset-format">${preset.format.toUpperCase()}</div>
        `;
        
        // クリックイベント
        card.addEventListener('click', () => this.selectPreset(id, card));
        
        return card;
    }
    
    getPresetIcon(presetId) {
        const iconMap = {
            'chrome_extension': '🌐',
            'macos_icon': '🍎',
            'favicon': '🔗'
        };
        return iconMap[presetId] || '📱';
    }
    
    selectPreset(presetId, cardElement) {
        // 既存の選択を解除
        document.querySelectorAll('.preset-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 新しい選択を設定
        cardElement.classList.add('selected');
        this.selectedPreset = presetId;
        
        // カスタムサイズ入力をクリア
        this.customSizes.value = '';
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }
    
    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }
    
    handleDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    processFile(file) {
        // ファイルタイプをチェック
        if (!file.type.startsWith('image/')) {
            this.showError('画像ファイルを選択してください');
            return;
        }
        
        // ファイルサイズをチェック（10MB制限）
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.showError('ファイルサイズが大きすぎます（10MB以下にしてください）');
            return;
        }
        
        this.selectedFile = file;
        this.showPreview(file);
        this.hideError();
    }
    
    showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            this.previewImage.src = e.target.result;
            this.imageInfo.textContent = `${file.name} (${this.formatFileSize(file.size)})`;
            this.previewArea.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
    
    clearPreview() {
        this.selectedFile = null;
        this.previewArea.style.display = 'none';
        this.fileInput.value = '';
        this.hideError();
    }
    
    async handleCustomResize() {
        if (!this.selectedFile) {
            this.showError('画像を選択してください');
            return;
        }
        
        const customSizes = this.customSizes.value.trim();
        if (!customSizes) {
            this.showError('カスタムサイズを入力してください');
            return;
        }
        
        // サイズの妥当性をチェック
        const sizes = customSizes.split(',').map(s => parseInt(s.trim())).filter(s => !isNaN(s) && s > 0);
        if (sizes.length === 0) {
            this.showError('有効なサイズを入力してください（例: 16,32,48）');
            return;
        }
        
        await this.resizeImage(null, sizes);
    }
    
    async resizeImage(presetId, customSizes = null) {
        if (!this.selectedFile) {
            this.showError('画像を選択してください');
            return;
        }
        
        this.showProcessing();
        this.hideError();
        
        try {
            const formData = new FormData();
            formData.append('image', this.selectedFile);
            
            if (presetId) {
                formData.append('preset_id', presetId);
            } else if (customSizes) {
                formData.append('custom_sizes', customSizes.join(','));
            } else {
                throw new Error('プリセットまたはカスタムサイズを選択してください');
            }
            
            const response = await fetch('/api/resize', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`サーバーエラー: ${response.status} - ${errorText}`);
            }
            
            // レスポンスをファイルとしてダウンロード
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // ファイル名を設定（filename* 優先 → filename quoted → filename unquoted）
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'resized_icons';
            if (contentDisposition) {
                let m = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
                if (m && m[1]) {
                    try { filename = decodeURIComponent(m[1]); } catch (_) { filename = m[1]; }
                } else {
                    m = contentDisposition.match(/filename\s*=\s*\"([^\"]+)\"/i);
                    if (m && m[1]) {
                        filename = m[1];
                    } else {
                        m = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
                        if (m && m[1]) filename = m[1].trim();
                    }
                }
            }
            
            // 拡張子が無い場合はContent-Typeから推測して補完
            if (!/\.[A-Za-z0-9]+$/.test(filename)) {
                const ct = response.headers.get('Content-Type') || '';
                if (ct.includes('image/png')) filename += '.png';
                else if (ct.includes('image/x-icon')) filename += '.ico';
                else if (ct.includes('application/zip')) filename += '.zip';
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('リサイズ処理に失敗しました:', error);
            this.showError(`リサイズ処理に失敗しました: ${error.message}`);
        } finally {
            this.hideProcessing();
        }
    }
    
    showProcessing() {
        this.processing.style.display = 'block';
    }
    
    hideProcessing() {
        this.processing.style.display = 'none';
    }
    
    showError(message) {
        this.errorMessage.querySelector('.error-text').textContent = message;
        this.errorMessage.style.display = 'flex';
    }
    
    hideError() {
        this.errorMessage.style.display = 'none';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// プリセットカードのクリックイベントをグローバルに設定
document.addEventListener('click', (e) => {
    const presetCard = e.target.closest('.preset-card');
    if (presetCard && window.iconResizer) {
        const presetId = presetCard.dataset.presetId;
        if (presetId) {
            window.iconResizer.resizeImage(presetId);
        }
    }
});

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', () => {
    window.iconResizer = new IconResizer();
});

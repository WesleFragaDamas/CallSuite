// static/js/layout_maquinas_interactions.js
document.addEventListener('DOMContentLoaded', function () {
    // --- Seletores Globais e Configurações ---
    const csrfTokenInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    const CSRF_TOKEN = csrfTokenInput ? csrfTokenInput.value : null;
    const URLS = (window.APP_CONFIG && window.APP_CONFIG.urls) ? window.APP_CONFIG.urls : {};

    const detailsModalEl = document.getElementById('computerDetailsModal');
    let detailsModal = null; if (detailsModalEl) detailsModal = new bootstrap.Modal(detailsModalEl);
    const detailsModalBody = document.getElementById('computerDetailsModalBody');
    const detailsModalLabel = document.getElementById('computerDetailsModalLabel');

    const reportModalEl = document.getElementById('reportProblemModal');
    let reportModal = null; if (reportModalEl) reportModal = new bootstrap.Modal(reportModalEl);
    const reportForm = document.getElementById('reportProblemForm');
    const reportCompNameEl = document.getElementById('report_comp_name');
    const reportCompIdInput = document.getElementById('report_computador_id');

    const layoutViewport = document.getElementById('layoutViewport');
    const layoutMapCanvas = document.getElementById('layoutMapCanvas');
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomResetBtn = document.getElementById('zoom-reset-btn');
    const zoomLevelDisplay = document.getElementById('zoom-level-display');
    const zoomFitBtn = document.getElementById('zoom-fit-btn'); // Botão para Zoom Fit

    let currentZoomLevel = 1.0;
    const ZOOM_STEP = 0.1;
    const MIN_ZOOM = 0.3;
    const MAX_ZOOM = 2.5;
    const GRID_SIZE = 20;

    const toggleEditModeBtn = document.getElementById('toggle-edit-mode-btn');
    let isEditMode = false;
    let draggedItem = null;
    let offsetX, offsetY;

    let isPanning = false, panStartX, panStartY, panScrollLeftStart, panScrollTopStart;

    let guidelineH = null;
    let guidelineV = null;
    const SMART_GUIDE_THRESHOLD = 8;

    if (!CSRF_TOKEN && (reportForm || document.querySelector('.form-atualizar-chamado'))) {
        console.warn("CSRF Token não encontrado. Formulários AJAX podem falhar.");
    }

    // --- Funções Auxiliares ---
    function showToast(message, type = 'info') {
        const container = document.querySelector('.toast-container');
        if (!container) { alert(message); return; }
        const id = 'toast-' + Date.now();
        const bgClass = (type === 'error' ? 'danger' : type);
        const html = `<div id="${id}" class="toast align-items-center text-white bg-${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true"><div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div></div>`;
        container.insertAdjacentHTML('beforeend', html);
        const el = document.getElementById(id);
        if (el) {
            const toast = new bootstrap.Toast(el, { delay: 5000 });
            toast.show();
            el.addEventListener('hidden.bs.toast', () => el.remove());
        }
    }

    function toggleButtonSpinner(button, isLoading, loadingText = "Aguarde...") {
        if (!button) return;
        if (isLoading) {
            button.dataset.originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalHtml || (button.querySelector('.bi') ? button.querySelector('.bi').outerHTML : "Ação");
        }
    }

    async function fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                let errorData = { error: `Erro HTTP: ${response.status} - ${response.statusText}` };
                try {
                    const jsonData = await response.json();
                    errorData = { ...errorData, ...jsonData };
                } catch (e) {
                    const text = await response.text(); // Pega o texto se não for JSON
                    errorData.responseText = text; // Adiciona ao objeto de erro
                    console.error("Server response (not JSON):", text);
                 }
                throw errorData;
            }
            // Só tenta parsear JSON se a resposta for OK.
             try {
                return await response.json();
            } catch (e) {
                // Se a resposta foi OK mas não é JSON válido (improvável se o backend estiver correto)
                console.error("Fetch success but response not JSON:", await response.text());
                throw { error: "Resposta inesperada do servidor." };
            }
        } catch (error) {
            console.error(`Fetch error for ${url}:`, error);
            throw error;
        }
    }

    // --- Lógica de Zoom ---
    function applyZoom(newZoom) {
        currentZoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, parseFloat(newZoom.toFixed(2))));
        if (layoutMapCanvas) layoutMapCanvas.style.transform = `scale(${currentZoomLevel})`;
        if (zoomLevelDisplay) zoomLevelDisplay.textContent = `${Math.round(currentZoomLevel * 100)}%`;
        updateZoomButtonsState();
    }

    function updateZoomButtonsState() {
        if (zoomInBtn) zoomInBtn.disabled = currentZoomLevel >= MAX_ZOOM;
        if (zoomOutBtn) zoomOutBtn.disabled = currentZoomLevel <= MIN_ZOOM;
    }

    // --- Lógica de Pan ---
    function startPan(e) {
        if ((e.target === layoutMapCanvas || e.target === layoutViewport) && layoutViewport) {
            isPanning = true;
            layoutViewport.classList.add('is-panning');
            panStartX = e.pageX - layoutViewport.offsetLeft;
            panStartY = e.pageY - layoutViewport.offsetTop;
            panScrollLeftStart = layoutViewport.scrollLeft;
            panScrollTopStart = layoutViewport.scrollTop;
        }
    }
    function doPan(e) {
        if (!isPanning || !layoutViewport) return;
        const x = e.pageX - layoutViewport.offsetLeft;
        const y = e.pageY - layoutViewport.offsetTop;
        layoutViewport.scrollLeft = panScrollLeftStart - (x - panStartX);
        layoutViewport.scrollTop = panScrollTopStart - (y - panStartY);
    }
    function endPan() {
        if (isPanning && layoutViewport) {
            isPanning = false;
            layoutViewport.classList.remove('is-panning');
        }
    }

    // --- Smart Guides ---
    function createGuidelines() {
        if (!layoutMapCanvas) return;
        if (!guidelineH) {
            guidelineH = document.createElement('div');
            guidelineH.className = 'smart-guideline-h';
            Object.assign(guidelineH.style, { position: 'absolute', display: 'none', backgroundColor: 'magenta', width: '100%', height: '1px', zIndex: '1001', pointerEvents: 'none' });
            layoutMapCanvas.appendChild(guidelineH);
        }
        if (!guidelineV) {
            guidelineV = document.createElement('div');
            guidelineV.className = 'smart-guideline-v';
            Object.assign(guidelineV.style, { position: 'absolute', display: 'none', backgroundColor: 'magenta', width: '1px', height: '100%', zIndex: '1001', pointerEvents: 'none' });
            layoutMapCanvas.appendChild(guidelineV);
        }
    }
    function clearSmartGuides() {
        if (guidelineH) guidelineH.style.display = 'none';
        if (guidelineV) guidelineV.style.display = 'none';
    }
     function showAndSnapSmartGuides(e, currentDraggedItem) {
        if (!isEditMode || !currentDraggedItem || !layoutMapCanvas || !guidelineV || !guidelineH) {
            clearSmartGuides();
            return;
        }
        clearSmartGuides(); // Limpa guias da iteração anterior

        // Posição atual do mouse para cálculo da posição do item (canto superior esquerdo do item)
        const canvasRect = layoutMapCanvas.getBoundingClientRect();
        let currentItemPotentialX = ((e.clientX - canvasRect.left) / currentZoomLevel) - offsetX;
        let currentItemPotentialY = ((e.clientY - canvasRect.top) / currentZoomLevel) - offsetY;

        const draggedWidth = currentDraggedItem.offsetWidth;
        const draggedHeight = currentDraggedItem.offsetHeight;

        // Coordenadas "snapped" que serão aplicadas ao item
        let snapX = currentItemPotentialX;
        let snapY = currentItemPotentialY;
        let didSnapX = false;
        let didSnapY = false;

        const allItems = layoutMapCanvas.querySelectorAll('.computador-layout-item');

        allItems.forEach(otherItem => {
            if (otherItem === currentDraggedItem) return; // Não comparar com ele mesmo

            const otherRect = { // Posições e dimensões do otherItem no canvas não escalado
                left: parseFloat(otherItem.style.left),
                top: parseFloat(otherItem.style.top),
                width: otherItem.offsetWidth,
                height: otherItem.offsetHeight
            };
            otherRect.right = otherRect.left + otherRect.width;
            otherRect.bottom = otherRect.top + otherRect.height;
            otherRect.centerX = otherRect.left + otherRect.width / 2;
            otherRect.centerY = otherRect.top + otherRect.height / 2;

            // Pontos de interesse do item sendo arrastado (baseado na posição potencial do mouse)
            const draggedItemPoints = {
                left: currentItemPotentialX,
                right: currentItemPotentialX + draggedWidth,
                centerX: currentItemPotentialX + draggedWidth / 2,
                top: currentItemPotentialY,
                bottom: currentItemPotentialY + draggedHeight,
                centerY: currentItemPotentialY + draggedHeight / 2
            };

            // --- VERIFICAÇÕES DE ALINHAMENTO VERTICAL (linhas verticais) ---
            // Alinhar borda ESQUERDA do arrastado com borda ESQUERDA do outro
            if (Math.abs(draggedItemPoints.left - otherRect.left) < SMART_GUIDE_THRESHOLD) {
                snapX = otherRect.left;
                guidelineV.style.left = `${otherRect.left}px`;
                guidelineV.style.display = 'block';
                didSnapX = true;
            }
            // Alinhar CENTRO H do arrastado com CENTRO H do outro
            else if (Math.abs(draggedItemPoints.centerX - otherRect.centerX) < SMART_GUIDE_THRESHOLD) {
                snapX = otherRect.centerX - draggedWidth / 2;
                guidelineV.style.left = `${otherRect.centerX}px`;
                guidelineV.style.display = 'block';
                didSnapX = true;
            }
            // Alinhar borda DIREITA do arrastado com borda DIREITA do outro
            else if (Math.abs(draggedItemPoints.right - otherRect.right) < SMART_GUIDE_THRESHOLD) {
                snapX = otherRect.right - draggedWidth;
                guidelineV.style.left = `${otherRect.right}px`;
                guidelineV.style.display = 'block';
                didSnapX = true;
            }
            // TODO: Adicionar mais verificações (Esquerda com Direita, Esquerda com Centro H, etc.)

            // --- VERIFICAÇÕES DE ALINHAMENTO HORIZONTAL (linhas horizontais) ---
            // Alinhar TOPO do arrastado com TOPO do outro
            if (Math.abs(draggedItemPoints.top - otherRect.top) < SMART_GUIDE_THRESHOLD) {
                snapY = otherRect.top;
                guidelineH.style.top = `${otherRect.top}px`;
                guidelineH.style.display = 'block';
                didSnapY = true;
            }
            // Alinhar CENTRO V do arrastado com CENTRO V do outro
            else if (Math.abs(draggedItemPoints.centerY - otherRect.centerY) < SMART_GUIDE_THRESHOLD) {
                snapY = otherRect.centerY - draggedHeight / 2;
                guidelineH.style.top = `${otherRect.centerY}px`;
                guidelineH.style.display = 'block';
                didSnapY = true;
            }
            // Alinhar BASE do arrastado com BASE do outro
            else if (Math.abs(draggedItemPoints.bottom - otherRect.bottom) < SMART_GUIDE_THRESHOLD) {
                snapY = otherRect.bottom - draggedHeight;
                guidelineH.style.top = `${otherRect.bottom}px`;
                guidelineH.style.display = 'block';
                didSnapY = true;
            }
            // TODO: Adicionar mais verificações (Topo com Base, Topo com Centro V, etc.)

            // Se já deu snap nas duas direções com este otherItem, pode parar de verificar outros (otimização)
            // if (didSnapX && didSnapY) return; // Cuidado com o forEach, 'return' só sai da iteração atual.
        });

        // TODO: Adicionar verificações de alinhamento com as bordas/centro do CANVAS

        // Atualiza a posição visual do item sendo arrastado para a posição "snapped"
        currentDraggedItem.style.left = `${didSnapX ? snapX : currentItemPotentialX}px`;
        currentDraggedItem.style.top = `${didSnapY ? snapY : currentItemPotentialY}px`;
    }

    // --- Lógica de Drag & Drop e Modo de Edição ---
    function toggleLayoutEditMode() {
        if (!layoutMapCanvas || !toggleEditModeBtn) return;
        isEditMode = !isEditMode;
        layoutMapCanvas.classList.toggle('edit-mode', isEditMode);
        toggleEditModeBtn.classList.toggle('active', isEditMode);
        toggleEditModeBtn.innerHTML = isEditMode ? '<i class="bi bi-check-circle-fill"></i> Concluir' : '<i class="bi bi-pencil-square"></i> Editar Layout';
        toggleEditModeBtn.title = isEditMode ? "Concluir Edição" : "Ativar Edição";

        document.querySelectorAll('.computador-layout-item').forEach(item => {
            item.setAttribute('draggable', isEditMode);
            if (isEditMode) {
                item.addEventListener('dragstart', handleDragStart);
                item.addEventListener('dragend', handleDragEnd);
            } else {
                item.removeEventListener('dragstart', handleDragStart);
                item.removeEventListener('dragend', handleDragEnd);
            }
        });
        console.log(isEditMode ? "Modo de edição ATIVADO." : "Modo de edição desativado.");
    }

    function handleDragStart(e) {
        if (!isEditMode) { e.preventDefault(); return; }
        draggedItem = e.currentTarget;
        createGuidelines();
        const rect = draggedItem.getBoundingClientRect();
        offsetX = (e.clientX - rect.left) / currentZoomLevel;
        offsetY = (e.clientY - rect.top) / currentZoomLevel;
        e.dataTransfer.setData('text/plain', draggedItem.id);
        e.dataTransfer.effectAllowed = 'move';
        draggedItem.classList.add('is-dragging');
    }

    function handleDragEnd(e) {
        if (draggedItem) draggedItem.classList.remove('is-dragging');
        draggedItem = null;
        clearSmartGuides();
    }

    function handleDragOver(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        showAndSnapSmartGuides(e, draggedItem);
    }

    async function handleDrop(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault();
        clearSmartGuides();

        let finalX = parseFloat(draggedItem.style.left); // Já ajustado pelo showAndSnapSmartGuides
        let finalY = parseFloat(draggedItem.style.top);

        // Snap-to-grid final
        finalX = Math.max(0, Math.round(finalX / GRID_SIZE) * GRID_SIZE);
        finalY = Math.max(0, Math.round(finalY / GRID_SIZE) * GRID_SIZE);

        draggedItem.style.left = `${finalX}px`;
        draggedItem.style.top = `${finalY}px`;

        const compId = draggedItem.dataset.compIdCard;
        const compName = draggedItem.querySelector('h6')?.textContent.trim() || 'Computador';

        if (!URLS.updateComputadorPosition) {
            showToast('URL de salvamento não configurada.', 'danger'); return;
        }
        const saveUrl = URLS.updateComputadorPosition.replace('__COMP_ID__', compId);

        if (CSRF_TOKEN) {
            try {
                const data = await fetchData(saveUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({ pos_x: finalX, pos_y: finalY })
                });
                if (!data.success) throw (data.error || 'Falha ao salvar.');
                // console.log(`Posição de ${compName} salva!`); // Log silencioso
            } catch (error) {
                showToast(`Erro ao salvar posição: ${error.error || error.message || error}`, 'danger');
            }
        } else { showToast('CSRF Token ausente. Posição não salva.', 'warning'); }
    }

    // --- Zoom Fit to Content ---
    function calculateAndApplyZoomFit() {
        if (!layoutMapCanvas || !layoutViewport) {
            console.error("ZoomFit: Elementos do canvas ou viewport não encontrados.");
            return;
        }

        // Usar as dimensões definidas para o canvas (do CSS ou JS)
        // offsetWidth/Height podem não ser o ideal aqui se o canvas for muito maior
        // que o conteúdo e quisermos ver o canvas "vazio".
        // Se o canvas tem width/height no style, use isso, senão offsetWidth.
        // Assumindo que layoutMapCanvas.style.width e height estão definidos em 'px'
        // No nosso CSS, definimos width: 2500px e height: 1800px para layoutMapCanvas.
        const canvasWidth = parseFloat(getComputedStyle(layoutMapCanvas).width) || layoutMapCanvas.scrollWidth;
        const canvasHeight = parseFloat(getComputedStyle(layoutMapCanvas).height) || layoutMapCanvas.scrollHeight;

        if (canvasWidth <= 0 || canvasHeight <= 0) {
            console.warn("ZoomFit: Dimensões do canvas inválidas ou não detectadas.");
            applyZoom(1.0); // Reseta para zoom 100%
            if (layoutViewport) {
                layoutViewport.scrollLeft = 0;
                layoutViewport.scrollTop = 0;
            }
            return;
        }

        const viewportWidth = layoutViewport.clientWidth;
        const viewportHeight = layoutViewport.clientHeight;

        // Adicionar um pequeno padding visual (ex: 98% da viewport para não encostar nas bordas)
        const PADDING_FACTOR = 0.98;
        const zoomX = (viewportWidth * PADDING_FACTOR) / canvasWidth;
        const zoomY = (viewportHeight * PADDING_FACTOR) / canvasHeight;

        // Usar o menor fator de zoom para garantir que todo o canvas caiba
        let newZoom = Math.min(zoomX, zoomY);

        // Respeitar os limites de MIN_ZOOM e MAX_ZOOM que já temos
        // (Embora para "fit to canvas", o newZoom calculado possa ser menor que MIN_ZOOM)
        // Se quiser que o "fit" possa ir abaixo do MIN_ZOOM manual, remova esta linha:
        newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));


        applyZoom(newZoom); // Aplica o novo nível de zoom

        // Centralizar o canvas dentro da viewport após o zoom fit
        // (ou simplesmente alinhar ao canto superior esquerdo se preferir)
        if (layoutViewport) {
            // Para centralizar:
            const scaledCanvasWidth = canvasWidth * currentZoomLevel;
            const scaledCanvasHeight = canvasHeight * currentZoomLevel;

            layoutViewport.scrollLeft = (scaledCanvasWidth - viewportWidth) / 2;
            layoutViewport.scrollTop = (scaledCanvasHeight - viewportHeight) / 2;

            // Para alinhar no canto superior esquerdo:
            // layoutViewport.scrollLeft = 0;
            // layoutViewport.scrollTop = 0;
        }
        console.log(`Zoom Fit to Canvas: Nível=${newZoom.toFixed(2)}`);
    }



    // --- Atualizar Aparência do Card no Layout ---
    function updateComputerCardOnLayout(compId, reportStatus = {}, pingStatus = {}) {
        const card = document.querySelector(`.computador-layout-item[data-comp-id-card="${compId}"]`);
        if (!card) return;

        if (Object.keys(reportStatus).length > 0) {
            card.classList.remove('status-ok', 'status-problema', 'status-manutencao');
            if (reportStatus.status_reportado_class) card.classList.add(reportStatus.status_reportado_class);
            card.style.backgroundColor = reportStatus.status_reportado_class === 'status-problema' ? '#f8d7da' : (reportStatus.status_reportado_class === 'status-manutencao' ? '#fff3cd' : '#fff');
            const statusBadge = card.querySelector('.status-reportado-text-badge');
            if (statusBadge && reportStatus.status_reportado_display) {
                statusBadge.textContent = reportStatus.status_reportado_display;
                let badgeBg = 'bg-secondary-subtle text-secondary-emphasis';
                if (reportStatus.status_reportado_class === 'status-ok') badgeBg = 'bg-success-subtle text-success-emphasis';
                else if (reportStatus.status_reportado_class === 'status-problema') badgeBg = 'bg-danger-subtle text-danger-emphasis';
                else if (reportStatus.status_reportado_class === 'status-manutencao') badgeBg = 'bg-warning-subtle text-warning-emphasis';
                statusBadge.className = `status-reportado-text-badge badge rounded-pill small ${badgeBg}`;
            }
        }

        if (Object.keys(pingStatus).length > 0) {
            const pingIndicatorCard = card.querySelector(`#ping-status-${compId}`);
            if (pingIndicatorCard && pingStatus.ping_icon_html) {
                pingIndicatorCard.innerHTML = pingStatus.ping_icon_html;
                if (pingStatus.ping_text_class) pingIndicatorCard.className = `ping-indicator ${pingStatus.ping_text_class}`;
            }
            const prefix = 'status-rede-';
            card.className = card.className.replace(new RegExp(prefix + '\\S*', 'g'), '').trim();
            if (pingStatus.ping_online_status) card.classList.add(prefix + pingStatus.ping_online_status);
        }
    }

   // --- Manipuladores de Eventos para Modais e Ping ---
    async function handleViewComputerDetails(event) {
        const cardItem = event.currentTarget;
        const compId = cardItem.dataset.compIdCard;
        if (!detailsModal || !compId || !detailsModalBody || !detailsModalLabel) return;

        const compName = cardItem.querySelector('h6')?.textContent.trim() || 'Computador';
        detailsModalLabel.textContent = `Detalhes de: ${compName}`;
        detailsModalBody.innerHTML = '<p class="text-center my-3"><span class="spinner-border spinner-border-sm"></span> Carregando...</p>';
        detailsModal.show();

        try {
            const data = await fetchData(`/assets/computador/${compId}/detalhes/`);
            if (data.success && data.html_content) {
                detailsModalBody.innerHTML = data.html_content;
            } else { throw (data.error || 'Conteúdo não recebido.'); }
        } catch (error) {
            detailsModalBody.innerHTML = `<p class="text-danger">Falha ao carregar: ${error.error || error.message || error}</p>`;
        }
    }

    function handleOpenReportProblemModal(triggerButton) {
        if (!reportModal || !reportForm || !reportCompIdInput || !reportCompNameEl) return;
        const compId = triggerButton.dataset.compId;
        const compName = triggerButton.dataset.compName;
        reportCompIdInput.value = compId;
        reportCompNameEl.textContent = compName;
        reportForm.reset();
        reportModal.show();
    }

    async function handleSubmitReportProblemForm(event) {
        event.preventDefault();
        if (!CSRF_TOKEN) { showToast('Erro de segurança.', 'danger'); return; }
        const submitButton = reportForm.querySelector('button[type="submit"]');
        toggleButtonSpinner(submitButton, true, "Enviando...");
        try {
            const data = await fetchData(URLS.reportarProblema, {
                method: 'POST', body: new FormData(reportForm), headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            if (data.success) {
                showToast(data.message || 'Chamado aberto!', 'success');
                reportModal.hide();
                updateComputerCardOnLayout(data.computador_id, {
                    status_reportado_class: data.novo_status_class,
                    status_reportado_display: data.novo_status_computador
                });
                const currentDetailCompId = detailsModalBody.querySelector('[data-computador-id-modal-content]')?.dataset.computadorIdModalContent;
                if (detailsModalEl && detailsModalEl.classList.contains('show') && currentDetailCompId === String(data.computador_id)) {
                    const cardTrigger = document.querySelector(`.computador-layout-item[data-comp-id-card="${data.computador_id}"]`);
                    if (cardTrigger) handleViewComputerDetails({ currentTarget: cardTrigger });
                }
            } else { throw (data.error || 'Erro desconhecido.'); }
        } catch (error) {
            showToast(`Erro: ${error.error || error.message || error}`, 'danger');
        } finally {
            toggleButtonSpinner(submitButton, false);
        }
    }

    async function handleSubmitUpdateTicketForm(event) {
        event.preventDefault();
        if (!CSRF_TOKEN) { showToast('Erro de segurança.', 'danger'); return; }
        const form = event.target;
        const submitButton = form.querySelector('button[type="submit"]');
        toggleButtonSpinner(submitButton, true, "Atualizando...");
        try {
            const data = await fetchData(URLS.atualizarChamado, {
                method: 'POST', body: new FormData(form), headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            if (data.success) {
                showToast(data.message || 'Chamado atualizado!', 'success');
                const modalContentDiv = form.closest('[data-computador-id-modal-content]');
                if (modalContentDiv) {
                    const compIdForModal = modalContentDiv.dataset.computadorIdModalContent;
                    if (data.html_chamados_atualizado) modalContentDiv.querySelector(`#lista-chamados-container-${compIdForModal}`).innerHTML = data.html_chamados_atualizado;
                    if (data.html_form_chamado_atualizado) modalContentDiv.querySelector(`#form-atualizar-chamado-container-${compIdForModal}`).innerHTML = data.html_form_chamado_atualizado;
                }
                updateComputerCardOnLayout(data.computador_id, {
                    status_reportado_class: data.computador_status_reportado_class,
                    status_reportado_display: data.computador_status_reportado_display
                });
            } else { throw (data.error || 'Erro desconhecido.'); }
        } catch (error) {
            showToast(`Erro: ${error.error || error.message || error}`, 'danger');
        } finally {
            toggleButtonSpinner(submitButton, false);
        }
    }

    async function handlePingCheck(pingButton) {
        const compId = pingButton.dataset.compId;
        toggleButtonSpinner(pingButton, true, "");
        try {
            const data = await fetchData(`/assets/computador/${compId}/ping/`, {
                headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' }
            });
            if (data.success) {
                let iconHtml = '<i class="bi bi-question-circle text-muted"></i>', textClass = 'text-muted';
                if (data.online_status === 'online') { iconHtml = '<i class="bi bi-wifi text-success"></i>'; textClass = 'text-success'; }
                else if (data.online_status === 'offline') { iconHtml = '<i class="bi bi-wifi-off text-danger"></i>'; textClass = 'text-danger'; }
                else if (data.online_status === 'unreachable') { iconHtml = '<i class="bi bi-exclamation-diamond-fill text-warning"></i>'; textClass = 'text-warning'; }
                else if (data.online_status === 'timeout') { iconHtml = '<i class="bi bi-hourglass-split text-warning"></i>'; textClass = 'text-warning'; }
                else if (data.online_status === 'no_ip') { iconHtml = '<i class="bi bi-ethernet text-muted"></i>'; textClass = 'text-muted';}

                const modalPingSpan = detailsModalBody.querySelector(`#ping-status-modal-${compId}`);
                if (modalPingSpan && detailsModalEl && detailsModalEl.classList.contains('show')) {
                    modalPingSpan.innerHTML = data.status_text || 'Desconhecido';
                    modalPingSpan.className = `badge ${data.status_class || 'bg-secondary'}`;
                }
                updateComputerCardOnLayout(compId, {}, {
                    ping_icon_html: iconHtml, ping_text_class: textClass, ping_online_status: data.online_status
                });
            } else { throw (data.error || 'Falha no ping.'); }
        } catch (error) {
            showToast(`Ping Erro: ${error.error || error.message || error}`, 'danger');
            updateComputerCardOnLayout(compId, {}, {ping_icon_html: '<i class="bi bi-x-circle-fill text-dark"></i>'});
        } finally {
            toggleButtonSpinner(pingButton, false);
        }
    }

    // --- Atribuição de Event Listeners ---
    if (layoutMapCanvas && layoutViewport) {
        if (zoomInBtn) zoomInBtn.addEventListener('click', () => applyZoom(currentZoomLevel + ZOOM_STEP));
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => applyZoom(currentZoomLevel - ZOOM_STEP));
        if (zoomResetBtn) zoomResetBtn.addEventListener('click', () => applyZoom(1.0));
        if (toggleEditModeBtn) toggleEditModeBtn.addEventListener('click', toggleLayoutEditMode);
        if (zoomFitBtn) zoomFitBtn.addEventListener('click', calculateAndApplyZoomFit); // Listener para Zoom Fit

        layoutViewport.addEventListener('mousedown', startPan);
        layoutViewport.addEventListener('wheel', function(event) {
            if (event.ctrlKey) { event.preventDefault(); applyZoom(currentZoomLevel - (Math.sign(event.deltaY) * ZOOM_STEP));}
        }, { passive: false });

        layoutMapCanvas.addEventListener('dragover', handleDragOver);
        layoutMapCanvas.addEventListener('drop', handleDrop);

        updateZoomButtonsState();
        if (layoutMapCanvas.querySelectorAll('.computador-layout-item').length > 0) {
            setTimeout(calculateAndApplyZoomFit, 150); // Zoom fit na carga inicial
        } else {
            applyZoom(currentZoomLevel); // Aplica zoom 1.0 se não houver itens
        }
    }
    document.addEventListener('mousemove', doPan);
    document.addEventListener('mouseup', endPan);

    document.querySelectorAll('.computador-layout-item.can-open-details').forEach(card => {
        card.addEventListener('click', function(event) {
            if (isEditMode || event.target.closest('.btn-check-ping')) return;
            handleViewComputerDetails(event);
        });
    });

    document.querySelectorAll('.btn-check-ping').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
            handlePingCheck(event.currentTarget);
        });
    });

    if (detailsModalBody) {
        detailsModalBody.addEventListener('click', function(event) {
            const reportBtn = event.target.closest('.btn-abrir-modal-reportar-problema-detalhes');
            const pingBtn = event.target.closest('.btn-check-ping-modal');
            if (reportBtn) { event.preventDefault(); handleOpenReportProblemModal(reportBtn); }
            else if (pingBtn) { event.preventDefault(); event.stopPropagation(); handlePingCheck(pingBtn); }
        });
    }

    if (reportForm) reportForm.addEventListener('submit', handleSubmitReportProblemForm);
    document.body.addEventListener('submit', function(event) {
        if (event.target && event.target.matches('.form-atualizar-chamado')) {
            handleSubmitUpdateTicketForm(event);
        }
    });

    console.log("JS: layout_maquinas_interactions.js vFinal carregado.");
});
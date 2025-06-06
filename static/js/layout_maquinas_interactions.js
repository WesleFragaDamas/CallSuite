// static/js/layout_maquinas_interactions.js
document.addEventListener('DOMContentLoaded', function () {
    // --- Seletores Globais e Configurações ---
    const csrfTokenInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    const CSRF_TOKEN = csrfTokenInput ? csrfTokenInput.value : null;
    const URLS = (window.APP_CONFIG && window.APP_CONFIG.urls) ? window.APP_CONFIG.urls : {};

    const detailsModalEl = document.getElementById('computerDetailsModal');
    let detailsModal = null; // Inicializa como null, será instanciado se o elemento existir
    if (detailsModalEl) {
        detailsModal = new bootstrap.Modal(detailsModalEl);
    }
    const detailsModalBody = document.getElementById('computerDetailsModalBody');
    const detailsModalLabel = document.getElementById('computerDetailsModalLabel');

    const reportModalEl = document.getElementById('reportProblemModal');
    let reportModal = null;
    if (reportModalEl) {
        reportModal = new bootstrap.Modal(reportModalEl);
    }
    const reportForm = document.getElementById('reportProblemForm');
    const reportCompNameEl = document.getElementById('report_comp_name');
    const reportCompIdInput = document.getElementById('report_computador_id');

    const layoutViewport = document.getElementById('layoutViewport');
    const layoutMapCanvas = document.getElementById('layoutMapCanvas');
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomResetBtn = document.getElementById('zoom-reset-btn');
    const zoomLevelDisplay = document.getElementById('zoom-level-display');

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

    if (!CSRF_TOKEN && (reportForm || document.querySelector('.form-atualizar-chamado'))) {
        console.warn("CSRF Token não encontrado no DOM inicial. Se houver formulários AJAX, eles podem falhar sem ele.");
        // showToast('Erro de segurança (CS). Recarregue.', 'danger'); // Pode ser muito intrusivo se não houver forms ainda
    }

    // --- Funções Auxiliares ---
    function showToast(message, type = 'info') {
        const container = document.querySelector('.toast-container'); // Assegure-se que este container existe no seu base.html
        if (!container) {
            console.warn("Toast container não encontrado. Usando alert como fallback.");
            alert(message);
            return;
        }
        const id = 'toast-' + Date.now();
        const bgClass = (type === 'error' ? 'danger' : type); // Bootstrap usa 'danger' para erro
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
            if (button.dataset.originalHtml) {
                button.innerHTML = button.dataset.originalHtml;
            } else {
                // Fallback se originalHtml não foi setado (ex: se o botão não tinha texto)
                 if (button.querySelector('.bi')) button.innerHTML = button.querySelector('.bi').outerHTML; // Mantém só o ícone se houver
                 else button.textContent = "Ação"; // Texto genérico
            }
        }
    }

    async function fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                let errorData = { error: `Erro HTTP: ${response.status} - ${response.statusText}` };
                try {
                    // Tenta parsear como JSON, mas se falhar, usa o erro HTTP genérico
                    const jsonData = await response.json();
                    errorData = { ...errorData, ...jsonData }; // Mescla o erro HTTP com o JSON do backend
                } catch (e) { /* Não faz nada se não for JSON, mantém o erro HTTP */ }
                throw errorData;
            }
            return await response.json(); // Só chama json() se response.ok
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
        if (e.target === layoutMapCanvas || e.target === layoutViewport) {
            isPanning = true;
            if (layoutViewport) layoutViewport.classList.add('is-panning');
            panStartX = e.pageX - (layoutViewport ? layoutViewport.offsetLeft : 0);
            panStartY = e.pageY - (layoutViewport ? layoutViewport.offsetTop : 0);
            panScrollLeftStart = layoutViewport ? layoutViewport.scrollLeft : 0;
            panScrollTopStart = layoutViewport ? layoutViewport.scrollTop : 0;
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
        if (isPanning) {
            isPanning = false;
            if (layoutViewport) layoutViewport.classList.remove('is-panning');
        }
    }

    // --- Lógica de Drag & Drop e Modo de Edição ---
    function toggleLayoutEditMode() {
        if (!layoutMapCanvas || !toggleEditModeBtn) return;
        isEditMode = !isEditMode;
        layoutMapCanvas.classList.toggle('edit-mode', isEditMode);
        toggleEditModeBtn.classList.toggle('active', isEditMode);
        const pencilIcon = '<i class="bi bi-pencil-square"></i> Editar Layout';
        const checkIcon = '<i class="bi bi-check-circle-fill"></i> Concluir Edição';
        toggleEditModeBtn.innerHTML = isEditMode ? checkIcon : pencilIcon;
        toggleEditModeBtn.title = isEditMode ? "Sair do Modo de Edição" : "Ativar Edição de Layout";

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
        const rect = draggedItem.getBoundingClientRect();
        offsetX = (e.clientX - rect.left) / currentZoomLevel;
        offsetY = (e.clientY - rect.top) / currentZoomLevel;
        e.dataTransfer.setData('text/plain', draggedItem.id); // Necessário para Firefox e outros
        e.dataTransfer.effectAllowed = 'move';
        draggedItem.classList.add('is-dragging');
    }

    function handleDragEnd(e) {
        if (draggedItem) draggedItem.classList.remove('is-dragging');
        draggedItem = null;
    }

    function handleDragOver(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    async function handleDrop(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault();

        const canvasRect = layoutMapCanvas.getBoundingClientRect();
        let newX = ((e.clientX - canvasRect.left) / currentZoomLevel) - offsetX;
        let newY = ((e.clientY - canvasRect.top) / currentZoomLevel) - offsetY;

        newX = Math.max(0, Math.round(newX / GRID_SIZE) * GRID_SIZE);
        newY = Math.max(0, Math.round(newY / GRID_SIZE) * GRID_SIZE);

        draggedItem.style.left = `${newX}px`;
        draggedItem.style.top = `${newY}px`;

        const compId = draggedItem.dataset.compIdCard;
        const compName = draggedItem.querySelector('h6')?.textContent.trim() || 'Computador';

        if (!URLS.updateComputadorPosition) {
            showToast('URL de salvamento não configurada.', 'danger');
            console.error("URLS.updateComputadorPosition não definida.");
            return;
        }
        const saveUrl = URLS.updateComputadorPosition.replace('__COMP_ID__', compId);

        if (CSRF_TOKEN) {
            try {
                const data = await fetchData(saveUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({ pos_x: newX, pos_y: newY })
                });
                if (data.success) {
                    showToast(data.message || `Posição de ${compName} salva!`, 'success');
                } else { throw (data.error || 'Falha ao salvar.'); }
            } catch (error) {
                showToast(`Erro ao salvar: ${error.error || error.message || error}`, 'danger');
            }
        } else { showToast('CSRF Token ausente. Posição não salva.', 'warning'); }
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

     // --- NOVO: SELETOR PARA O BOTÃO DE ZOOM FIT ---
    const zoomFitBtn = document.getElementById('zoom-fit-btn');

    // --- NOVA FUNÇÃO: CALCULAR E APLICAR ZOOM FIT ---
    function calculateAndApplyZoomFitToCanvas() {
    if (!layoutMapCanvas || !layoutViewport) return;

    const canvasWidth = layoutMapCanvas.scrollWidth; // Largura total do conteúdo do canvas
    const canvasHeight = layoutMapCanvas.scrollHeight; // Altura total do conteúdo do canvas
    // Ou, se você tem as dimensões do canvas definidas no JS ou como data-attributes:
    // const canvasWidth = parseFloat(layoutMapCanvas.style.width) || layoutMapCanvas.offsetWidth;
    // const canvasHeight = parseFloat(layoutMapCanvas.style.height) || layoutMapCanvas.offsetHeight;


    if (canvasWidth <= 0 || canvasHeight <= 0) {
        applyZoom(1.0); return;
    }

    const viewportWidth = layoutViewport.clientWidth;
    const viewportHeight = layoutViewport.clientHeight;

    const PADDING_PERCENT = 0.98; // Um padding bem pequeno para não encostar nas bordas
    const zoomX = (viewportWidth * PADDING_PERCENT) / canvasWidth;
    const zoomY = (viewportHeight * PADDING_PERCENT) / canvasHeight;

    let newZoom = Math.min(zoomX, zoomY);
    newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));

    applyZoom(newZoom);

    // Resetar scroll para o canto superior esquerdo ao ajustar ao canvas inteiro
    layoutViewport.scrollLeft = 0;
    layoutViewport.scrollTop = 0;

    console.log(`Zoom Fit to Canvas: Nível=${newZoom.toFixed(2)}`);
    }

    // --- Atribuição de Event Listeners ---
    if (layoutMapCanvas && layoutViewport) {
        if (zoomInBtn) zoomInBtn.addEventListener('click', () => applyZoom(currentZoomLevel + ZOOM_STEP));
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => applyZoom(currentZoomLevel - ZOOM_STEP));
        if (zoomResetBtn) zoomResetBtn.addEventListener('click', () => applyZoom(1.0));
        if (toggleEditModeBtn) toggleEditModeBtn.addEventListener('click', toggleLayoutEditMode);

        layoutViewport.addEventListener('mousedown', startPan);
        layoutViewport.addEventListener('wheel', function(event) {
            if (event.ctrlKey) { event.preventDefault(); applyZoom(currentZoomLevel - (Math.sign(event.deltaY) * ZOOM_STEP));}
        }, { passive: false });

        layoutMapCanvas.addEventListener('dragover', handleDragOver);
        layoutMapCanvas.addEventListener('drop', handleDrop);

        updateZoomButtonsState();
        applyZoom(currentZoomLevel); // Aplica estado inicial do zoom
    }
    document.addEventListener('mousemove', doPan);
    document.addEventListener('mouseup', endPan);

    document.querySelectorAll('.computador-layout-item.can-open-details').forEach(card => {
        card.addEventListener('click', function(event) {
            if (event.target.closest('.btn-check-ping') || isEditMode) { // Não abre modal se clicou no ping ou está em modo de edição
                return;
            }
            handleViewComputerDetails(event);
        });
    });

    document.querySelectorAll('.btn-check-ping').forEach(button => { // Botões de ping nos cards
        button.addEventListener('click', function(event) {
            event.stopPropagation(); // Impede que o clique propague para o card
            handlePingCheck(event.currentTarget);
        });
    });

    if (detailsModalBody) { // Delegação para botões DENTRO do modal de detalhes
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

    // Verificação final de elementos (opcional, para depuração)
    const essentialElements = {CSRF_TOKEN, URLS, detailsModalEl, reportModalEl, layoutViewport, layoutMapCanvas};
    for (const key in essentialElements) {
        if (!essentialElements[key] && !(key === 'URLS' && Object.keys(URLS).length === 0) && !(key === 'CSRF_TOKEN' && CSRF_TOKEN === null && !reportForm && !document.querySelector('.form-atualizar-chamado'))) {
            // console.warn(`JS Init Warning: Elemento/configuração essencial "${key}" não encontrado.`);
        }
    }
    console.log("JS: layout_maquinas_interactions.js carregado e todos os listeners configurados.");

     if (zoomFitBtn) {
        zoomFitBtn.addEventListener('click', calculateAndApplyZoomFit);
    }

    // É uma boa ideia chamar o calculateAndApplyZoomFit na carga inicial da página
    // se houver computadores, para que o layout já comece bem enquadrado.
    if (layoutMapCanvas && layoutMapCanvas.querySelectorAll('.computador-layout-item').length > 0) {
        // setTimeout para dar tempo ao navegador de renderizar e calcular offsetWidth/Height corretamente
        setTimeout(calculateAndApplyZoomFit, 100);
    } else if (layoutMapCanvas) { // Se não há itens, apenas reseta o zoom
        applyZoom(1.0);
    }
});
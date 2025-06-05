// static/js/layout_maquinas_interactions.js
document.addEventListener('DOMContentLoaded', function () {
    // --- Seletores Globais e Configurações ---
    const csrfTokenInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    const CSRF_TOKEN = csrfTokenInput ? csrfTokenInput.value : null;
    const URLS = (window.APP_CONFIG && window.APP_CONFIG.urls) ? window.APP_CONFIG.urls : {};

    const detailsModalEl = document.getElementById('computerDetailsModal');
    const detailsModal = detailsModalEl ? new bootstrap.Modal(detailsModalEl) : null;
    const detailsModalBody = document.getElementById('computerDetailsModalBody');
    const detailsModalLabel = document.getElementById('computerDetailsModalLabel');

    const reportModalEl = document.getElementById('reportProblemModal');
    const reportModal = reportModalEl ? new bootstrap.Modal(reportModalEl) : null;
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

    // --- Funções Auxiliares ---
    function showToast(message, type = 'info') {
        const container = document.querySelector('.toast-container');
        if (!container) { alert(message); return; }
        const id = 'toast-' + Date.now();
        const html = `<div id="${id}" class="toast bg-${type} text-white" role="alert"><div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`;
        container.insertAdjacentHTML('beforeend', html);
        const el = document.getElementById(id);
        new bootstrap.Toast(el, { delay: 5000 }).show();
        el.addEventListener('hidden.bs.toast', () => el.remove());
    }

    function toggleButtonSpinner(button, isLoading, loadingText = "Aguarde...") {
        if (isLoading) {
            button.dataset.originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> ${loadingText}`;
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalHtml || "Enviar";
        }
    }

    async function fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `Erro HTTP: ${response.status}` }));
                throw errorData;
            }
            return await response.json();
        } catch (error) {
            console.error(`Fetch error for ${url}:`, error);
            throw error; // Re-throw para ser pego pelo chamador
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
    let isPanning = false, panStartX, panStartY, panScrollLeftStart, panScrollTopStart;
    function startPan(e) {
        // Inicia o pan somente se o clique for no fundo do viewport ou canvas
        if (e.target === layoutMapCanvas || e.target === layoutViewport) {
            isPanning = true;
            layoutViewport.classList.add('is-panning');
            panStartX = e.pageX - layoutViewport.offsetLeft;
            panStartY = e.pageY - layoutViewport.offsetTop;
            panScrollLeftStart = layoutViewport.scrollLeft;
            panScrollTopStart = layoutViewport.scrollTop;
            // e.preventDefault(); // Pode ser necessário se houver seleção de texto
        }
    }
    function doPan(e) {
        if (!isPanning) return;
        // e.preventDefault(); // Previne scroll padrão da página apenas se estiver arrastando
        const x = e.pageX - layoutViewport.offsetLeft;
        const y = e.pageY - layoutViewport.offsetTop;
        layoutViewport.scrollLeft = panScrollLeftStart - (x - panStartX);
        layoutViewport.scrollTop = panScrollTopStart - (y - panStartY);
    }
    function endPan() {
        if (isPanning) {
            isPanning = false;
            layoutViewport.classList.remove('is-panning');
        }
    }

    // --- Atualizar Aparência do Card no Layout ---
    function updateComputerCardOnLayout(compId, statusData) {
        const card = document.querySelector(`.computador-layout-item[data-comp-id-card="${compId}"]`);
        if (!card) return;

        card.classList.remove('status-ok', 'status-problema', 'status-manutencao');
        if (statusData.status_reportado_class) card.classList.add(statusData.status_reportado_class);

        card.style.backgroundColor = statusData.status_reportado_class === 'status-problema' ? '#f8d7da' : (statusData.status_reportado_class === 'status-manutencao' ? '#fff3cd' : '#fff');

        const statusBadge = card.querySelector('.status-reportado-text-badge');
        if (statusBadge && statusData.status_reportado_display) {
            statusBadge.textContent = statusData.status_reportado_display;
            let badgeBgClass = 'bg-secondary-subtle text-secondary-emphasis';
            if (statusData.status_reportado_class === 'status-ok') badgeBgClass = 'bg-success-subtle text-success-emphasis';
            else if (statusData.status_reportado_class === 'status-problema') badgeBgClass = 'bg-danger-subtle text-danger-emphasis';
            else if (statusData.status_reportado_class === 'status-manutencao') badgeBgClass = 'bg-warning-subtle text-warning-emphasis';
            statusBadge.className = `status-reportado-text-badge badge rounded-pill small ${badgeBgClass}`;
        }

        // Atualiza ícone de ping no card
        const pingIndicatorCard = card.querySelector(`#ping-status-${compId}`);
        if (pingIndicatorCard && statusData.ping_icon_html && statusData.ping_text_class) {
            pingIndicatorCard.innerHTML = statusData.ping_icon_html;
            pingIndicatorCard.className = `ping-indicator ${statusData.ping_text_class}`;
        }
        const cardNetworkStatusClassPrefix = 'status-rede-';
        card.className = card.className.replace(new RegExp(cardNetworkStatusClassPrefix + '\\S*', 'g'), '').trim();
        if (statusData.ping_online_status) card.classList.add(cardNetworkStatusClassPrefix + statusData.ping_online_status);

    }

    // --- Manipuladores de Eventos Principais ---
    async function handleViewComputerDetails(event) {
        const cardItem = event.currentTarget; // O .computador-layout-item
        const compId = cardItem.dataset.compIdCard;
        if (!detailsModal || !compId) return;

        const compName = cardItem.querySelector('h6')?.textContent.trim() || 'Computador';
        detailsModalLabel.textContent = `Detalhes de: ${compName}`;
        detailsModalBody.innerHTML = '<p class="text-center my-3"><span class="spinner-border spinner-border-sm"></span> Carregando...</p>';
        detailsModal.show();

        try {
            const data = await fetchData(`/assets/computador/${compId}/detalhes/`);
            if (data.success && data.html_content) {
                detailsModalBody.innerHTML = data.html_content;
            } else {
                throw (data.error || 'Conteúdo não recebido.');
            }
        } catch (error) {
            detailsModalBody.innerHTML = `<p class="text-danger">Falha ao carregar: ${error.error || error.message || error}</p>`;
        }
    }

    function handleOpenReportProblemModal(triggerButton) {
        if (!reportModal || !reportForm) return;
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
                method: 'POST',
                body: new FormData(reportForm),
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            if (data.success) {
                showToast(data.message || 'Chamado aberto!', 'success');
                reportModal.hide();
                updateComputerCardOnLayout(data.computador_id, {
                    status_reportado_class: data.novo_status_class,
                    status_reportado_display: data.novo_status_computador
                });
                // Recarregar detalhes no modal se estiver aberto para este PC
                const currentDetailCompId = detailsModalBody.querySelector('[data-computador-id-modal-content]')?.dataset.computadorIdModalContent;
                 if (detailsModalEl.classList.contains('show') && currentDetailCompId === String(data.computador_id)) {
                    const cardTrigger = document.querySelector(`.computador-layout-item[data-comp-id-card="${data.computador_id}"]`);
                    if(cardTrigger) handleViewComputerDetails({currentTarget: cardTrigger}); // Simula clique para recarregar
                }
            } else {
                throw (data.error || 'Erro desconhecido.');
            }
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
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-CSRFToken': CSRF_TOKEN }
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
            } else {
                throw (data.error || 'Erro desconhecido.');
            }
        } catch (error) {
            showToast(`Erro: ${error.error || error.message || error}`, 'danger');
        } finally {
            toggleButtonSpinner(submitButton, false);
        }
    }

    async function handlePingCheck(pingButton) {
        const compId = pingButton.dataset.compId;
        toggleButtonSpinner(pingButton, true, ""); // Spinner sem texto
        try {
            const data = await fetchData(`/assets/computador/${compId}/ping/`, {
                headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' }
            });
            if (data.success) {
                let iconHtml = '<i class="bi bi-question-circle text-muted"></i>', textClass = 'text-muted';
                if (data.online_status === 'online') { iconHtml = '<i class="bi bi-wifi text-success"></i>'; textClass = 'text-success'; }
                // ... (outras condições de ícone e classe como na sua versão anterior) ...
                else if (data.online_status === 'offline') { iconHtml = '<i class="bi bi-wifi-off text-danger"></i>'; textClass = 'text-danger'; }
                else if (data.online_status === 'unreachable') { iconHtml = '<i class="bi bi-exclamation-diamond-fill text-warning"></i>'; textClass = 'text-warning'; }
                else if (data.online_status === 'timeout') { iconHtml = '<i class="bi bi-hourglass-split text-warning"></i>'; textClass = 'text-warning'; }
                else if (data.online_status === 'no_ip') { iconHtml = '<i class="bi bi-ethernet text-muted"></i>'; textClass = 'text-muted';}


                // Atualiza no modal de detalhes, se estiver aberto e for o mesmo PC
                const modalPingSpan = detailsModalBody.querySelector(`#ping-status-modal-${compId}`);
                if (modalPingSpan && detailsModalEl.classList.contains('show')) {
                    modalPingSpan.innerHTML = data.status_text || 'Desconhecido';
                    modalPingSpan.className = `badge ${data.status_class || 'bg-secondary'}`;
                }
                // Atualiza no card do layout
                updateComputerCardOnLayout(compId, {}, { // Passa objeto vazio para status_reportado se não muda
                    ping_icon_html: iconHtml,
                    ping_text_class: textClass,
                    ping_online_status: data.online_status
                });
            } else {
                throw (data.error || 'Falha no ping.');
            }
        } catch (error) {
            showToast(`Ping Erro: ${error.error || error.message || error}`, 'danger');
            updateComputerCardOnLayout(compId, {}, {ping_icon_html: '<i class="bi bi-x-circle-fill text-dark"></i>'});
        } finally {
            toggleButtonSpinner(pingButton, false);
        }
    }

     // --- VARIÁVEIS E SELETORES PARA MODO DE EDIÇÃO E DRAG & DROP ---
    const toggleEditModeBtn = document.getElementById('toggle-edit-mode-btn');
    let isEditMode = false;
    let draggedItem = null; // Item sendo arrastado
    let offsetX, offsetY;   // Offset do mouse dentro do item arrastado

    // --- FUNÇÕES PARA MODO DE EDIÇÃO E DRAG & DROP ---
    function toggleLayoutEditMode() {
        isEditMode = !isEditMode;
        layoutMapCanvas.classList.toggle('edit-mode', isEditMode);
        toggleEditModeBtn.classList.toggle('active', isEditMode);
        toggleEditModeBtn.innerHTML = isEditMode ?
            '<i class="bi bi-check-circle-fill"></i> Concluir Edição' :
            '<i class="bi bi-pencil-square"></i> Editar Layout';
        toggleEditModeBtn.title = isEditMode ?
            "Salvar e Sair do Modo de Edição" :
            "Ativar Modo de Edição de Layout";

        document.querySelectorAll('.computador-layout-item').forEach(item => {
            item.setAttribute('draggable', isEditMode);
            if (isEditMode) {
                // Adiciona listeners de drag quando o modo de edição é ativado
                item.addEventListener('dragstart', handleDragStart);
                item.addEventListener('dragend', handleDragEnd);
            } else {
                // Remove listeners de drag quando o modo de edição é desativado
                item.removeEventListener('dragstart', handleDragStart);
                item.removeEventListener('dragend', handleDragEnd);
            }
        });

        if (!isEditMode) {
            // Aqui poderíamos ter uma lógica para "salvar todas as posições alteradas" se não salvarmos a cada drop.
            // Por enquanto, salvaremos a cada drop.
            console.log("Modo de edição desativado.");
        } else {
            console.log("Modo de edição ATIVADO.");
        }
    }

    function handleDragStart(e) {
        if (!isEditMode) return;
        draggedItem = e.target.closest('.computador-layout-item'); // Garante que pegamos o item correto

        // Calcular o offset do clique do mouse em relação ao canto superior esquerdo do item arrastado
        // Isso ajuda a manter o item posicionado corretamente sob o mouse durante o arraste.
        const rect = draggedItem.getBoundingClientRect(); // Coordenadas relativas à viewport
        // As coordenadas de e.clientX/Y também são relativas à viewport.
        // Precisamos do offset DENTRO do elemento, considerando o zoom do canvas.
        offsetX = (e.clientX - rect.left) / currentZoomLevel;
        offsetY = (e.clientY - rect.top) / currentZoomLevel;

        e.dataTransfer.setData('text/plain', draggedItem.id); // Necessário para o Firefox
        // e.dataTransfer.effectAllowed = 'move'; // Define o tipo de operação permitida
        // Adicionar uma classe para estilizar o item sendo arrastado (opcional)
        draggedItem.classList.add('is-dragging');
        // console.log("Drag Start:", draggedItem.id, "Offset X:", offsetX, "Offset Y:", offsetY);
    }

    function handleDragEnd(e) {
        if (draggedItem) {
            draggedItem.classList.remove('is-dragging');
        }
        draggedItem = null;
        // console.log("Drag End");
    }

    function handleDragOver(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault(); // ESSENCIAL para permitir o drop
        // e.dataTransfer.dropEffect = 'move'; // Indica visualmente que é um local de drop válido
    }

    async function handleDrop(e) {
        if (!isEditMode || !draggedItem) return;
        e.preventDefault();
        draggedItem.classList.remove('is-dragging');

        const canvasRect = layoutMapCanvas.getBoundingClientRect(); // Coordenadas e tamanho do canvas na viewport

        // Coordenadas do mouse relativas à viewport
        let clientX = e.clientX;
        let clientY = e.clientY;

        // Posição do canto superior esquerdo do canvas na viewport
        let canvasLeft = canvasRect.left;
        let canvasTop = canvasRect.top;

        // Calcular a posição do mouse DENTRO do canvas, ajustando pelo scroll da viewport
        // e pelo offset que calculamos no dragstart.
        // As coordenadas são relativas ao canvas NÃO ESCALADO.
        let newX = (clientX - canvasLeft) / currentZoomLevel - offsetX;
        let newY = (clientY - canvasTop) / currentZoomLevel - offsetY;

        // Arredondar para inteiros e garantir que não seja negativo (opcional)
        newX = Math.max(0, Math.round(newX));
        newY = Math.max(0, Math.round(newY));

        // Atualizar visualmente a posição do item
        draggedItem.style.left = `${newX}px`;
        draggedItem.style.top = `${newY}px`;

        const compId = draggedItem.dataset.compIdCard;
        console.log(`Dropped ${compId} at (Canvas Coords): X=${newX}, Y=${newY}. Zoom: ${currentZoomLevel}`);

        // Enviar para o backend para salvar
        if (CSRF_TOKEN) {
            try {
                const response = await fetch(`/assets/computador/${compId}/update-position/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN
                    },
                    body: JSON.stringify({ pos_x: newX, pos_y: newY })
                });
                const data = await response.json();
                if (data.success) {
                    showToast(data.message || `Posição de ${draggedItem.querySelector('h6')?.textContent.trim()} salva!`, 'success');
                } else {
                    throw (data.error || 'Falha ao salvar posição.');
                }
            } catch (error) {
                showToast(`Erro ao salvar posição: ${error}`, 'danger');
                // Reverter a posição visual se o save falhar? (mais complexo)
                console.error("Save position error:", error);
            }
        } else {
            showToast('CSRF Token não encontrado. Posição não salva.', 'warning');
        }
        draggedItem = null;
    }

    // --- Atribuição de Event Listeners ---

     if (toggleEditModeBtn) {
        toggleEditModeBtn.addEventListener('click', toggleLayoutEditMode);
    }

    if (layoutMapCanvas) { // Listeners relacionados ao layout/zoom/pan

        layoutMapCanvas.addEventListener('dragover', handleDragOver);
        layoutMapCanvas.addEventListener('drop', handleDrop);

        if (zoomInBtn) zoomInBtn.addEventListener('click', () => applyZoom(currentZoomLevel + ZOOM_STEP));
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => applyZoom(currentZoomLevel - ZOOM_STEP));
        if (zoomResetBtn) zoomResetBtn.addEventListener('click', () => applyZoom(1.0));
        if (layoutViewport) { // Listeners de Pan e Wheel Zoom
             layoutViewport.addEventListener('mousedown', startPan);
             layoutViewport.addEventListener('wheel', function(event) {
                if (event.ctrlKey) {
                    event.preventDefault();
                    applyZoom(currentZoomLevel - (Math.sign(event.deltaY) * ZOOM_STEP));
                }
            }, { passive: false });
        }
        updateZoomButtonsState();
        applyZoom(currentZoomLevel); // Aplica zoom inicial
    }
    // Listener global para mousemove e mouseup para o Pan
    document.addEventListener('mousemove', doPan);
    document.addEventListener('mouseup', endPan);


    document.querySelectorAll('.computador-layout-item.can-open-details').forEach(card => {
        card.addEventListener('click', handleViewComputerDetails);
    });

    document.querySelectorAll('.btn-check-ping').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation(); // IMPEDE que o clique no botão de ping abra o modal de detalhes
            handlePingCheck(event.currentTarget);
        });
    });

    if (detailsModalBody) { // Delegação para botões DENTRO do modal de detalhes
        detailsModalBody.addEventListener('click', function(event) {
            const reportBtnTrigger = event.target.closest('.btn-abrir-modal-reportar-problema-detalhes');
            const pingBtnModalTrigger = event.target.closest('.btn-check-ping-modal');

            if (reportBtnTrigger) { event.preventDefault(); handleOpenReportProblemModal(reportBtnTrigger); }
            else if (pingBtnModalTrigger) { event.preventDefault(); event.stopPropagation(); handlePingCheck(pingBtnModalTrigger); }
        });
    }

    if (reportForm) reportForm.addEventListener('submit', handleSubmitReportProblemForm);

    document.body.addEventListener('submit', function(event) { // Delegação para form de ATUALIZAR chamado
        if (event.target && event.target.matches('.form-atualizar-chamado')) {
            handleSubmitUpdateTicketForm(event);
        }
    });

    // Verifica se todos os elementos principais foram encontrados
    if (!CSRF_TOKEN || !URLS.reportarProblema || !detailsModalEl || !reportModalEl || !layoutViewport || !layoutMapCanvas) {
        console.warn("Um ou mais elementos/configurações principais não foram encontrados. Algumas funcionalidades podem não operar corretamente.");
    }
});
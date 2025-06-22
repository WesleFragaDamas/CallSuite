// static/js/erlang_calculator_utils.js

/**
 * Calcula o fatorial de um número.
 * @param {number} n - O número (será arredondado para o inteiro mais próximo).
 * @returns {number|NaN} - O fatorial de n, ou NaN se n for negativo.
 */
function factorialJs(n_float) {
    let n = Math.floor(n_float);
    if (n < 0) return NaN;
    if (n === 0 || n === 1) return 1;
    let result = 1;
    for (let i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

/**
 * Calcula a Probabilidade de Espera (Pw) usando a fórmula de Erlang C.
 * @param {number} A - Intensidade de tráfego (Erlangs). (Ex: chamadasPorHora * tmaEmSegundos / 3600)
 * @param {number} N - Número de agentes (deve ser um inteiro).
 * @returns {number} - A probabilidade de uma chamada ter que esperar (entre 0 e 1).
 */
function erlangCProbabilityOfWaiting(A, N_float) {
    let N = Math.floor(N_float);

    if (N <= 0) return 1.0; // Nenhuma posição, todas as chamadas esperam (ou são perdidas)
    if (A <= 0) return 0.0; // Sem tráfego, sem espera

    // A fórmula clássica de Erlang C requer N > A para estabilidade.
    if (N <= A) {
        // Se N <= A, a fila teoricamente cresce indefinidamente. Pw tende a 1.
        // Para evitar divisão por zero se N=A, e para refletir alta probabilidade de espera.
        return 0.9999999; // Representa uma probabilidade de espera muito alta
    }

    try {
        let sumatoriaTermos = 0;
        for (let k = 0; k < N; k++) { // Soma de k=0 até N-1
            const termoK = Math.pow(A, k) / factorialJs(k);
            // Verifica se o termo se tornou muito grande ou inválido
            if (!isFinite(termoK)) {
                sumatoriaTermos = Infinity; // Se qualquer termo é infinito, a soma é infinita
                break;
            }
            sumatoriaTermos += termoK;
        }

        // Se a somatória já é infinita, Pw será muito próximo de 0 (se N > A), o que não faz sentido.
        // Isso pode acontecer se A for muito grande em relação a N.
        // No entanto, o caso N <= A já deve cobrir a sobrecarga.
        if (!isFinite(sumatoriaTermos)) {
             // Se N > A mas a soma é infinita, algo está muito errado com os inputs, Pw deveria ser baixo.
             // Isso é improvável se N > A e A é razoável.
             console.warn("Erlang C: Somatória infinita com N > A. A=", A, "N=", N);
             return 0.0000001; // Retorna uma Pw muito baixa
        }

        const termoPrincipalNumerador = Math.pow(A, N) / factorialJs(N);
        const termoPrincipalDenominador = (N - A);

        if (!isFinite(termoPrincipalNumerador) || termoPrincipalDenominador <= 0) {
            // Se N=A, denominador é 0. Se N<A, é negativo, o que não faz sentido para este termo.
            // O caso N <= A já foi tratado acima, então N-A deve ser > 0.
            console.warn("Erlang C: Problema no termo principal. A=", A, "N=", N);
            return 0.9999999; // Pw alta se houver problema aqui
        }

        const termoPrincipal = termoPrincipalNumerador * (N / termoPrincipalDenominador);

        if (!isFinite(termoPrincipal)){
            console.warn("Erlang C: Termo principal infinito. A=", A, "N=", N);
            return 0.9999999;
        }

        if (sumatoriaTermos + termoPrincipal === 0) {
            // Evita divisão por zero, embora improvável se A > 0.
            // Se A > 0, termoPrincipal e sumatoriaTermos (para k=0) devem ser > 0.
            return 1.0;
        }

        let Pw = termoPrincipal / (sumatoriaTermos + termoPrincipal);
        return Math.max(0, Math.min(Pw, 1.0)); // Garante Pw entre 0 e 1

    } catch (e) {
        console.error("Erro crítico em erlangCProbabilityOfWaiting:", e, "A:", A, "N:", N);
        return 0.9999999; // Em caso de erro numérico não previsto
    }
}

/**
 * Calcula o Nível de Serviço (SL) - percentual de chamadas atendidas dentro do tempo alvo.
 * @param {number} A - Intensidade de tráfego (Erlangs).
 * @param {number} N - Número de agentes.
 * @param {number} tmaSeconds - Tempo Médio de Atendimento em segundos.
 * @param {number} targetTimeSeconds - Tempo alvo de espera em segundos (ex: 20s).
 * @returns {number} - Nível de Serviço como uma fração (0 a 1).
 */
function calculateServiceLevelJs(A, N_float, tmaSeconds, targetTimeSeconds) {
    let N = Math.floor(N_float);

    if (N <= 0 || tmaSeconds <= 0) return 0.0;
    if (A <= 0) return 1.0;
    // Se N <= A, o SL será muito baixo ou zero, pois a capacidade não supera a demanda.
    // A função Pw já retorna um valor alto para N <= A.
    // if (N <= A) return 0.000001; // Pode ser desnecessário se Pw lida bem.

    const Pw = erlangCProbabilityOfWaiting(A, N);

    // Se N=A, N-A = 0, exp(0) = 1. SL = 1 - Pw. Se Pw é 0.99999, SL é minúsculo.
    // Se N < A, N-A é negativo, exp(positivo) é > 1. SL = 1 - Pw*grande_numero, pode ser negativo.
    // Por isso, é importante que N > A para esta fórmula de SL ser mais estável.
    if (N <= A) { // Garante que não teremos SL negativo ou irreal
        return 0.000001;
    }

    const exponent = -(N - A) * (targetTimeSeconds / tmaSeconds);

    let serviceLevel;
    try {
        serviceLevel = 1.0 - (Pw * Math.exp(exponent));
    } catch (e) {
        console.error("Erro em Math.exp no calculateServiceLevelJs:", e, "Expoente:", exponent);
        serviceLevel = 0.0;
    }

    return Math.max(0, Math.min(serviceLevel, 1.0));
}

/**
 * Calcula a Taxa de Ocupação dos Agentes.
 * @param {number} A - Intensidade de tráfego (Erlangs).
 * @param {number} N - Número de agentes.
 * @returns {number} - Taxa de ocupação como uma fração (0 a 1, ou >1 se sobrecarregado).
 */
function calculateOccupancyJs(A, N_float) {
    let N = Math.floor(N_float);
    if (N === 0) return A > 0 ? Infinity : 0.0; // Ocupação infinita se 0 agentes e há tráfego
    if (A === 0) return 0.0;

    const occupancy = A / N;
    // Não limitaremos a 1.0 aqui, para que a UI possa mostrar sobrecarga (ex: 110%)
    return occupancy;
}

// Você pode adicionar outras funções utilitárias do seu projeto aqui se forem necessárias.
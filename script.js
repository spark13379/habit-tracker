// Habit Tracker - Script principal (versão melhorada)

// Constantes
const AUTH_TOKEN_KEY = 'habit_tracker_token';
const API_URL = 'http://localhost:8000';

// Elementos DOM
const authSection = document.getElementById('auth');
const habitForm = document.getElementById('habit-form');
const habitList = document.getElementById('habit-list');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const habitNameInput = document.getElementById('habit-name');
const habitDateInput = document.getElementById('habit-date');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
  checkAuthStatus();
});

// Verifica se o usuário está autenticado
function checkAuthStatus() {
  const token = getToken();
  
  if (token) {
    authSection.style.display = 'none';
    habitForm.style.display = 'block';
    loadHabits();
  }
}

// Armazenamento do token
function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

// Funções de autenticação
async function login() {
  try {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    
    if (!username || !password) {
      showAlert('Por favor, preencha todos os campos', 'error');
      return;
    }

    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);

    const response = await fetch(`${API_BASE_URL}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form
    });

    if (!response.ok) {
      throw new Error('Credenciais inválidas');
    }

    const data = await response.json();
    setToken(data.access_token);
    checkAuthStatus();
    showAlert('Login realizado com sucesso!', 'success');
    
  } catch (error) {
    console.error('Login error:', error);
    showAlert(error.message || 'Erro ao fazer login', 'error');
  }
}

async function register() {
  try {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    
    if (!username || !password) {
      showAlert('Por favor, preencha todos os campos', 'error');
      return;
    }

    if (password.length < 6) {
      showAlert('A senha deve ter pelo menos 6 caracteres', 'error');
      return;
    }

    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Erro ao registrar');
    }

    showAlert('Registro realizado com sucesso! Faça login.', 'success');
    
  } catch (error) {
    console.error('Register error:', error);
    showAlert(error.message || 'Erro ao registrar', 'error');
  }
}

function logout() {
  clearToken();
  authSection.style.display = 'block';
  habitForm.style.display = 'none';
  habitList.innerHTML = '';
  usernameInput.value = '';
  passwordInput.value = '';
  showAlert('Logout realizado com sucesso!', 'success');
}

// Funções de hábitos
async function loadHabits() {
  try {
    showLoading(true);
    
    const token = getToken();
    if (!token) return;

    const response = await fetch(`${API_BASE_URL}/habitos`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      if (response.status === 401) {
        logout();
        throw new Error('Sessão expirada. Faça login novamente.');
      }
      throw new Error('Falha ao carregar hábitos');
    }

    const habits = await response.json();
    renderHabits(habits);
    
  } catch (error) {
    console.error('Load habits error:', error);
    showAlert(error.message, 'error');
  } finally {
    showLoading(false);
  }
}

function renderHabits(habits) {
  habitList.innerHTML = '';
  
  if (habits.length === 0) {
    habitList.innerHTML = `<li class="empty-message">Nenhum hábito cadastrado ainda</li>`;
    return;
  }

  habits.forEach(habit => {
    habitList.appendChild(createHabitElement(habit));
  });
}

function createHabitElement(habit) {
  const li = document.createElement('li');
  li.className = 'habit-item';
  li.dataset.id = habit.id;
  
  if (habit.done) {
    li.classList.add('checked');
  }

  li.innerHTML = `
    <span class="habit-date">${formatDate(habit.date)}</span>
    <span class="habit-name">${habit.name}</span>
    <div class="habit-actions">
      <button class="delete-btn" data-id="${habit.id}">×</button>
    </div>
  `;

  // Marcar como feito
  li.addEventListener('click', async (e) => {
    if (!e.target.classList.contains('delete-btn') && !habit.done) {
      await toggleHabitDone(habit.id, li);
    }
  });

  // Deletar hábito
  const deleteBtn = li.querySelector('.delete-btn');
  deleteBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    await deleteHabit(habit.id, li);
  });

  return li;
}

async function toggleHabitDone(habitId, element) {
  try {
    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/habitos/${habitId}/feito`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) throw new Error('Falha ao atualizar hábito');

    element.classList.toggle('checked');
    showAlert('Hábito atualizado!', 'success');
    
  } catch (error) {
    console.error('Toggle habit error:', error);
    showAlert(error.message, 'error');
  }
}

async function deleteHabit(habitId, element) {
  try {
    if (!confirm('Tem certeza que deseja excluir este hábito?')) return;
    
    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/habitos/${habitId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) throw new Error('Falha ao excluir hábito');

    element.classList.add('fade-out');
    setTimeout(() => {
      element.remove();
      showAlert('Hábito excluído!', 'success');
    }, 300);
    
  } catch (error) {
    console.error('Delete habit error:', error);
    showAlert(error.message, 'error');
  }
}

// Adicionar novo hábito
habitForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  try {
    const name = habitNameInput.value.trim();
    const date = habitDateInput.value;
    
    if (!name || !date) {
      showAlert('Por favor, preencha todos os campos', 'error');
      return;
    }

    const token = getToken();
    const response = await fetch(`${API_BASE_URL}/habitos`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ name, date })
    });

    if (!response.ok) throw new Error('Falha ao criar hábito');

    habitNameInput.value = '';
    habitDateInput.value = '';
    loadHabits();
    showAlert('Hábito adicionado com sucesso!', 'success');
    
  } catch (error) {
    console.error('Add habit error:', error);
    showAlert(error.message, 'error');
  }
});

// Utilitários
function formatDate(dateString) {
  const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
  return new Date(dateString).toLocaleDateString('pt-BR', options);
}

function showAlert(message, type) {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  
  document.body.appendChild(alert);
  
  setTimeout(() => {
    alert.classList.add('fade-out');
    setTimeout(() => alert.remove(), 300);
  }, 3000);
}

function showLoading(show) {
  const loader = document.getElementById('loader') || createLoader();
  loader.style.display = show ? 'block' : 'none';
}

function createLoader() {
  const loader = document.createElement('div');
  loader.id = 'loader';
  loader.className = 'loader';
  loader.innerHTML = '<div class="spinner"></div>';
  document.body.appendChild(loader);
  return loader;
}

// Exportar funções para o escopo global (necessário para os botões no HTML)
window.login = login;
window.register = register;
window.logout = logout;
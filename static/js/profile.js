document.addEventListener('DOMContentLoaded', async () => {
    const profileRes = await apiGet('/api/auth/profile');
    if (profileRes.success) {
        const u = profileRes.user;
        document.getElementById('profileUsername').value = u.username;
        document.getElementById('profileFullName').value = u.full_name || '';
        document.getElementById('profileEmail').value = u.email;
        document.getElementById('profilePhone').value = u.phone_number || '';
        document.getElementById('profileCity').value = u.city || 'Mumbai';
        document.getElementById('profileRoutePref').value = u.route_preference || 'fastest';
        document.getElementById('memberSince').textContent = formatDateTime(u.created_at);
        document.getElementById('lastLogin').textContent = u.last_login
            ? formatDateTime(u.last_login) : 'Not logged in yet';
    }

    const [predRes, histRes] = await Promise.all([
        apiGet('/api/predict/count'),
        apiGet('/api/route/history'),
    ]);
    if (predRes.success) {
        document.getElementById('profilePredictions').textContent = predRes.count || 0;
    }
    if (histRes.success) {
        document.getElementById('profileTrips').textContent = histRes.history?.length || 0;
    }
});

// ── Update Profile ────────────────────────────────────────────────────────────
document.getElementById('profileForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const alertEl = document.getElementById('profileAlert');
    const res = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            full_name: form.full_name.value,
            email: form.email.value,
            phone_number: form.phone_number.value,
            city: form.city.value,
            route_preference: form.route_preference.value,
        })
    });
    const data = await res.json();
    alertEl.className = 'alert ' + (data.success ? 'alert-success' : 'alert-danger');
    alertEl.textContent = data.message || (data.success ? 'Profile updated' : 'Update failed');
    alertEl.classList.remove('d-none');
});

// ── Change Password ───────────────────────────────────────────────────────────
document.getElementById('changePwdForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const alertEl = document.getElementById('pwdAlert');
    alertEl.classList.add('d-none');

    if (form.new_password.value !== form.confirm_password.value) {
        alertEl.className = 'alert alert-danger';
        alertEl.textContent = 'New passwords do not match.';
        alertEl.classList.remove('d-none');
        return;
    }
    if (form.new_password.value.length < 6) {
        alertEl.className = 'alert alert-danger';
        alertEl.textContent = 'New password must be at least 6 characters.';
        alertEl.classList.remove('d-none');
        return;
    }

    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Updating...';

    try {
        const data = await apiPost('/api/auth/change-password', {
            current_password: form.current_password.value,
            new_password: form.new_password.value,
        });
        alertEl.className = 'alert ' + (data.success ? 'alert-success' : 'alert-danger');
        alertEl.textContent = data.message || (data.success ? 'Password updated!' : 'Failed to update password.');
        alertEl.classList.remove('d-none');
        if (data.success) form.reset();
    } catch {
        alertEl.className = 'alert alert-danger';
        alertEl.textContent = 'Cannot reach server.';
        alertEl.classList.remove('d-none');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Update Password';
    }
});

// ── Delete Account ────────────────────────────────────────────────────────────
document.getElementById('deleteAccountBtn').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to permanently delete your account? This cannot be undone.')) return;
    const confirm2 = prompt('Type DELETE to confirm:');
    if (confirm2 !== 'DELETE') { showToast('Account deletion cancelled.', 'info'); return; }

    try {
        const res = await fetch('/api/auth/delete-account', { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Your account has been deleted. Redirecting...', 'success');
            setTimeout(() => window.location.href = '/', 1500);
        } else {
            showToast(data.message || 'Failed to delete account.', 'danger');
        }
    } catch {
        showToast('Cannot reach server.', 'danger');
    }
});

// ── Feedback ──────────────────────────────────────────────────────────────────
document.getElementById('feedbackForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    const data = await apiPost('/api/analytics/feedback', {
        rating: parseInt(form.rating.value),
        comment: form.comment.value,
        feedback_type: 'general'
    });
    btn.disabled = false;
    if (data.success) {
        showToast('Thank you for your feedback! 😊', 'success');
        form.reset();
    } else {
        showToast(data.message || 'Failed to submit feedback.', 'danger');
    }
});

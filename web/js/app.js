const { createApp, ref, reactive, onMounted } = Vue;

const app = createApp({
    setup() {
        const API_BASE_URL = 'http://127.0.0.1:8000';
        const accounts = ref([]);
        const selectedAccount = ref(null);
        const errorMessage = ref('');
        const successMessage = ref('');
        
        // Bootstrap Modal instances
        let addAccountModal = null;
        let addZoneModal = null;
        let editAccountModal = null;
        let editZoneModal = null;

        // Initialize Bootstrap modals
        const initModals = () => {
            addAccountModal = new bootstrap.Modal(document.getElementById('addAccountModal'));
            addZoneModal = new bootstrap.Modal(document.getElementById('addZoneModal'));
            editAccountModal = new bootstrap.Modal(document.getElementById('editAccountModal'));
            editZoneModal = new bootstrap.Modal(document.getElementById('editZoneModal'));
        };

        // Notification handling
        const showError = (error) => {
            errorMessage.value = error.response?.data?.message || error.message || 'An error occurred';
            Toastify({
                text: errorMessage.value,
                style: {
                  background: "#dc3545",
                  color: "#fff",
                },
                duration: 3000,
                }).showToast();
        };

        const showSuccess = (message) => {
            successMessage.value = message;
            Toastify({
                text: successMessage.value,
                style: {
                  background: "#1acb79",
                  color: "#fff",
                },
                duration: 3000,
                }).showToast();
        };

        // Fetch all accounts
        const fetchAccounts = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/accounts`);
                accounts.value = response.data.data.accounts;
                if (accounts.value.length > 0 && !selectedAccount.value) {
                    selectedAccount.value = accounts.value[0];
                }
            } catch (error) {
                showError(error);
            }
        };

        // Account operations
        const showAddAccountModal = () => {
            Object.assign(newAccount, {
                useApiToken: false,
                useApiKey: false,
                apiToken: '',
                apiKey: '',
                email: ''
            });
            addAccountModal.show();
        };

        const addAccount = async () => {
            try {
                const accountData = {
                    authentication: {},
                    zones: []
                };

                if (newAccount.useApiToken) {
                    accountData.authentication.api_token = newAccount.apiToken;
                }

                if (newAccount.useApiKey) {
                    accountData.authentication.api_key = {
                        api_key: newAccount.apiKey,
                        account_email: newAccount.email
                    };
                }

                const response = await axios.post(`${API_BASE_URL}/accounts`, accountData);
                accounts.value.push(response.data.data.account);
                showSuccess(response.data.message);
                addAccountModal.hide();
            } catch (error) {
                showError(error);
            }
        };

        const showEditAccountModal = () => {
            if (!selectedAccount.value) return;

            const auth = selectedAccount.value.authentication;
            Object.assign(editAccount, {
                useApiToken: !!auth.api_token,
                useApiKey: !!auth.api_key,
                apiToken: auth.api_token || '',
                apiKey: auth.api_key?.api_key || '',
                email: auth.api_key?.account_email || ''
            });
            editAccountModal.show();
        };

        const updateAccount = async () => {
            try {
                const accountData = {
                    authentication: {},
                    zones: selectedAccount.value.zones
                };

                if (editAccount.useApiToken) {
                    accountData.authentication.api_token = editAccount.apiToken;
                }

                if (editAccount.useApiKey) {
                    accountData.authentication.api_key = {
                        api_key: editAccount.apiKey,
                        account_email: editAccount.email
                    };
                }

                const response = await axios.put(
                    `${API_BASE_URL}/accounts/${selectedAccount.value.id}`, 
                    accountData
                );
                
                // Update the account in the list
                const index = accounts.value.findIndex(a => a.id === selectedAccount.value.id);
                if (index !== -1) {
                    accounts.value[index] = response.data.data.account;
                    selectedAccount.value = response.data.data.account;
                }
                
                editAccountModal.hide();
                showSuccess(response.data.message);
            } catch (error) {
                showError(error);
            }
        };

        const deleteAccount = async (account) => {
            if (!confirm('Are you sure you want to delete this account?')) return;

            try {
                const response = await axios.delete(`${API_BASE_URL}/accounts/${account.id}`);
                accounts.value = accounts.value.filter(a => a.id !== account.id);
                if (selectedAccount.value?.id === account.id) {
                    selectedAccount.value = accounts.value.length > 0 ? accounts.value[0] : null;
                }
                showSuccess(response.data.message);
            } catch (error) {
                showError(error);
            }
        };

        // Zone operations
        const showAddZoneModal = () => {
            Object.assign(newZone, {
                zone_id: '',
                domain: '',
                subdomains: []
            });
            addZoneModal.show();
        };

        const addZone = async () => {
            try {
                const zone = {
                    zone_id: newZone.zone_id,
                    domain: newZone.domain,
                    subdomains: newZone.subdomains.map(s => ({
                        name: s.name,
                        proxied: s.proxied,
                        ttl: s.ttl
                    }))
                };
                const response = await axios.post(
                    `${API_BASE_URL}/accounts/${selectedAccount.value.id}/zones`,
                    zone
                );
                selectedAccount.value.zones.push(response.data.data.zone);
                // Update the account in the list
                const index = accounts.value.findIndex(a => a.id === selectedAccount.value.id);
                if (index !== -1) {
                    accounts.value[index] = selectedAccount.value;
                }
                addZoneModal.hide();
                showSuccess(response.data.message);
            } catch (error) {
                showError(error);
            }
        };

        const showEditZoneModal = (zone) => {
            Object.assign(editZone, {
                id: zone.id,
                zone_id: zone.zone_id,
                domain: zone.domain,
                subdomains: [...zone.subdomains]
            });
            editZoneModal.show();
        };

        const updateZone = async () => {
            try {
                const editedZone = {
                    zone_id: editZone.zone_id,
                    domain: editZone.domain,
                    subdomains: editZone.subdomains.map(s => ({
                        name: s.name,
                        proxied: s.proxied,
                        ttl: s.ttl || 1
                    }))
                };
                const response = await axios.put(
                    `${API_BASE_URL}/accounts/${selectedAccount.value.id}/zones/${editZone.id}`,
                    editedZone
                );
                
                // Update the zone in the account
                const zoneIndex = selectedAccount.value.zones.findIndex(z => z.id === editZone.id);
                if (zoneIndex !== -1) {
                    selectedAccount.value.zones[zoneIndex] = response.data.data.zone;
                    // Update the account in the list
                    const accountIndex = accounts.value.findIndex(a => a.id === selectedAccount.value.id);
                    if (accountIndex !== -1) {
                        accounts.value[accountIndex] = selectedAccount.value;
                    }
                }
                
                editZoneModal.hide();
                showSuccess(response.data.message);
            } catch (error) {
                showError(error);
            }
        };

        const deleteZone = async (zone) => {
            if (!confirm('Are you sure you want to delete this zone?')) return;

            try {
                const response = await axios.delete(
                    `${API_BASE_URL}/accounts/${selectedAccount.value.id}/zones/${zone.id}`
                );
                selectedAccount.value.zones = selectedAccount.value.zones.filter(z => z.id !== zone.id);
                // Update the account in the list
                const index = accounts.value.findIndex(a => a.id === selectedAccount.value.id);
                if (index !== -1) {
                    accounts.value[index] = selectedAccount.value;
                }
                showSuccess(response.data.message);
            } catch (error) {
                showError(error);
            }
        };

        // Subdomain operations
        const addSubdomain = () => {
            newZone.subdomains.push({
                name: '',
                proxied: false,
                ttl: 60
            });
        };

        const removeSubdomain = (index) => {
            newZone.subdomains.splice(index, 1);
        };

        const addEditSubdomain = () => {
            editZone.subdomains.push({
                name: '',
                proxied: false,
                ttl: 60
            });
        };

        const removeEditSubdomain = (index) => {
            editZone.subdomains.splice(index, 1);
        };

        // Utility functions
        const selectAccount = (account) => {
            selectedAccount.value = account;
        };

        const getAccountName = (account) => {
            if (account.authentication.api_key) {
                return account.authentication.api_key.account_email;
            }
            return `Account ${account.id.slice(0, 8)}`;
        };

        const maskToken = (token) => {
            if (!token) return '';
            return token.slice(0, 4) + '...' + token.slice(-4);
        };

        // Add Account Modal
        const newAccount = reactive({
            useApiToken: false,
            useApiKey: false,
            apiToken: '',
            apiKey: '',
            email: ''
        });

        // Add Zone Modal
        const newZone = reactive({
            zone_id: '',
            domain: '',
            subdomains: []
        });

        // Edit Account Modal
        const editAccount = reactive({
            useApiToken: false,
            useApiKey: false,
            apiToken: '',
            apiKey: '',
            email: ''
        });

        // Edit Zone Modal
        const editZone = reactive({
            id: '',
            zone_id: '',
            domain: '',
            subdomains: []
        });

        // Initialize
        onMounted(() => {
            initModals();
            fetchAccounts();
        });

        return {
            accounts,
            selectedAccount,
            newAccount,
            newZone,
            editAccount,
            editZone,
            errorMessage,
            successMessage,
            showAddAccountModal,
            addAccount,
            showEditAccountModal,
            updateAccount,
            deleteAccount,
            showAddZoneModal,
            addZone,
            showEditZoneModal,
            updateZone,
            deleteZone,
            addSubdomain,
            removeSubdomain,
            addEditSubdomain,
            removeEditSubdomain,
            selectAccount,
            getAccountName,
            maskToken
        };
    }
});

app.mount('#app');

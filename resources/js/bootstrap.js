import axios from 'axios';
window.axios = axios;

window.axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

const storedJwt = window.localStorage.getItem('tseyor_jwt');

if (storedJwt) {
    window.axios.defaults.headers.common.Authorization = `Bearer ${storedJwt}`;
}

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation, RefreshCw, ExternalLink } from 'lucide-react';

const regionCenters = {
  'Москва': [55.7558, 37.6173],
  'Московская область': [55.8319, 37.3292],
  'Краснодарский край': [45.0355, 38.9753],
  'Санкт-Петербург': [59.9343, 30.3351],
};

const officeNames = {
  tax: 'Инспекции ФНС',
  mfc: 'МФЦ «Мои документы»',
};

const officeCache = new Map();

function distanceKm(from, to) {
  const radians = value => value * Math.PI / 180;
  const dLat = radians(to[0] - from[0]);
  const dLon = radians(to[1] - from[1]);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(radians(from[0])) * Math.cos(radians(to[0])) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

async function findOffices(center, office, signal) {
  const [lat, lon] = center;
  const cacheKey = `${office}:${lat.toFixed(3)}:${lon.toFixed(3)}`;
  if (officeCache.has(cacheKey)) return officeCache.get(cacheKey);
  const latRadius = 12 / 111;
  const lonRadius = 12 / (111 * Math.cos(lat * Math.PI / 180));
  const bbox = [lon - lonRadius, lat - latRadius, lon + lonRadius, lat + latRadius].join(',');
  const url = new URL('https://photon.komoot.io/api/');
  url.search = new URLSearchParams({ q: office === 'tax' ? 'ФНС' : 'МФЦ', lat: String(lat), lon: String(lon), bbox, limit: '50' }).toString();
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error('Не удалось загрузить пункты');
  const data = await response.json();
  const found = data.features.map(item => {
    const tags = item.properties || {};
    if (!['government', 'public_service'].includes(tags.osm_value)) return null;
    if (/вход/i.test(tags.name || '')) return null;
    if (office === 'tax' && !/инспекция ФНС|ИФНС|управление ФНС/i.test(tags.name || '')) return null;
    const [itemLon, itemLat] = item.geometry.coordinates;
    const address = [tags.street, tags.housenumber].filter(Boolean).join(', ');
    return {
      id: `${tags.osm_type}-${tags.osm_id}`,
      name: tags.name,
      address: address || [tags.district, tags.city].filter(Boolean).join(', ') || 'Адрес уточните перед визитом',
      coords: [itemLat, itemLon],
      distance: distanceKm(center, [itemLat, itemLon]),
    };
  }).filter(item => item && item.distance <= 12).sort((a, b) => a.distance - b.distance);
  const offices = found.filter((item, index) => !found.slice(0, index).some(other =>
    other.name === item.name && distanceKm(other.coords, item.coords) < 0.15,
  )).slice(0, 8);
  officeCache.set(cacheKey, offices);
  return offices;
}

function OfficeMap({ center, offices, selected, onSelect }) {
  const container = useRef(null);
  const map = useRef(null);
  const layer = useRef(null);

  useEffect(() => {
    if (!container.current) return;
    map.current = L.map(container.current, { scrollWheelZoom: false }).setView(center, 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 18,
    }).addTo(map.current);
    layer.current = L.layerGroup().addTo(map.current);
    return () => { map.current?.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    if (!map.current || !layer.current) return;
    layer.current.clearLayers();
    const blue = L.divIcon({ className: 'office-map-icon', html: '<span></span>', iconSize: [22, 22], iconAnchor: [11, 11] });
    const user = L.divIcon({ className: 'office-map-user', html: '<span></span>', iconSize: [18, 18], iconAnchor: [9, 9] });
    L.marker(center, { icon: user }).addTo(layer.current).bindTooltip('Точка поиска');
    offices.forEach(office => L.marker(office.coords, { icon: blue }).addTo(layer.current).bindTooltip(office.name).on('click', () => onSelect(office.id)));
    const bounds = L.latLngBounds([center, ...offices.map(office => office.coords)]);
    map.current.fitBounds(bounds.pad(0.2), { maxZoom: 13 });
    setTimeout(() => map.current?.invalidateSize(), 0);
  }, [center, offices, onSelect]);

  useEffect(() => {
    const office = offices.find(item => item.id === selected);
    if (office) map.current?.panTo(office.coords);
  }, [selected, offices]);

  return <div className="office-map" ref={container} role="img" aria-label="Карта пунктов обслуживания OpenStreetMap" />;
}

export default function DocumentLocations({ office, region }) {
  const [center, setCenter] = useState(() => regionCenters[region] || null);
  const [positionType, setPositionType] = useState('region');
  const [offices, setOffices] = useState([]);
  const [status, setStatus] = useState('idle');
  const [selected, setSelected] = useState(null);
  const [locationError, setLocationError] = useState('');

  useEffect(() => {
    if (!center) return;
    const controller = new AbortController();
    setStatus('loading');
    setOffices([]);
    findOffices(center, office, controller.signal)
      .then(items => { setOffices(items); setStatus('ready'); })
      .catch(error => { if (error.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, [center, office]);

  function locate() {
    if (!navigator.geolocation) { setLocationError('Геолокация недоступна в этом браузере.'); return; }
    setLocationError('Определяем местоположение…');
    navigator.geolocation.getCurrentPosition(
      position => { setCenter([position.coords.latitude, position.coords.longitude]); setPositionType('current'); setLocationError(''); },
      () => setLocationError('Не удалось определить местоположение. Проверьте разрешение браузера.'),
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  return <div className="document-locations">
    <div className="locations-heading"><div><h2>Пункты получения и консультации</h2><p>{officeNames[office]} · {positionType === 'current' ? 'рядом с вами' : `рядом с центром региона: ${region}`}</p></div><button type="button" className="location-button" onClick={locate}><Navigation size={15} />Моё местоположение</button></div>
    {locationError && <p className="location-status" role="status">{locationError}</p>}
    {center ? <OfficeMap center={center} offices={offices} selected={selected} onSelect={setSelected} /> : <div className="location-empty">Укажите местоположение, чтобы найти пункты поблизости.</div>}
    {status === 'loading' && <p className="location-status"><RefreshCw size={14} className="spin" />Ищем пункты на карте…</p>}
    {status === 'error' && <p className="location-status">Не удалось загрузить пункты. Попробуйте позже или откройте карту напрямую.</p>}
    {status === 'ready' && offices.length === 0 && <p className="location-status">В радиусе 12 км подходящие пункты не найдены.</p>}
    {offices.map(item => <button type="button" key={item.id} className={`location-card ${selected === item.id ? 'selected' : ''}`} onClick={() => setSelected(item.id)}><span className="location-card-title"><MapPin size={16} /><strong>{item.name}</strong><b>{item.distance.toFixed(1)} км</b></span><span>{item.address}</span></button>)}
    {center && <a className="location-external" href={`https://www.openstreetmap.org/#map=14/${center[0]}/${center[1]}`} target="_blank" rel="noreferrer">Открыть карту <ExternalLink size={14} /></a>}
    <p className="locations-note">Пункты найдены по данным OpenStreetMap через Photon. Расстояние указано по прямой. Перед визитом проверьте адрес, часы работы и доступность услуги.</p>
  </div>;
}

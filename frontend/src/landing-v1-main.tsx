import React from 'react';
import { createRoot, hydrateRoot } from 'react-dom/client';
import LandingV1 from './landing/v1/LandingV1';

const root = document.getElementById('root')!;
const content = <React.StrictMode><LandingV1 /></React.StrictMode>;
if (root.hasChildNodes()) hydrateRoot(root, content);
else createRoot(root).render(content);

import { renderToString } from 'react-dom/server';
import LandingV1 from './landing/v1/LandingV1';

export function render() {
  return renderToString(<LandingV1 />);
}

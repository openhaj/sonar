/** Reward for catching a shooting star: Blåhaj flies by with your wish. */
import { assetUrl } from './env';
import { element, removeAfterAnimation, storage } from './util/dom';

export function makeAWish(): void {
  const count = Number(storage.get('wishes') ?? 0) + 1;
  storage.set('wishes', String(count));

  const shark = element('img', 'haj-wish', { alt: '' });
  shark.src = assetUrl('../img/blahaj.svg');
  removeAfterAnimation(shark);

  const toast = element('div', 'wish-toast', { role: 'status' });
  toast.textContent =
    count === 1
      ? 'You caught a shooting star! Make a wish - Blåhaj will carry it.'
      : `Shooting star #${count} caught! Blåhaj is on its way with your wish.`;
  removeAfterAnimation(toast);

  document.body.append(shark, toast);
}

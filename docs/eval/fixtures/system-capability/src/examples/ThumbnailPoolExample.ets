import { ThumbnailPool } from '../pools/ThumbnailPool'

export function runThumbnailPoolExample(): void {
  const pool = new ThumbnailPool(2)
  pool.storeThumbnail('cover-a', 'a.png')
  pool.storeThumbnail('cover-b', 'b.png')
}

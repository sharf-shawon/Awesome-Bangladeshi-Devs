## Why

Currently, the projects discovery page arbitrarily excludes repositories with 5 stars or fewer, omitting a vast portion of the community's work from being searchable. Additionally, rendering large volumes of projects at once poses browser performance risks, and the developer attributions on project cards are not hyperlinked to their respective profiles on the platform.

## What Changes

- **Complete Dataset**: Remove the minimum star threshold from the projects data generation to include all ~31,000 community repositories.
- **Lazy Loading**: Implement an infinite scroll / lazy-loading mechanism using `IntersectionObserver` to batch-render project cards and maintain UI responsiveness.
- **Profile Linking**: Wrap the developer avatar and username within the project cards with links pointing to their dedicated `/dev/<username>/` profile pages.
- **Search Optimization**: Tune the client-side Fuse.js configuration to handle the significantly larger dataset efficiently.

## Capabilities

### New Capabilities
- `projects-lazy-loading`: Mechanism to progressively render project cards as the user scrolls, ensuring browser stability with large datasets.

### Modified Capabilities
- `advanced-projects-search`: Update requirements to include all repositories regardless of star count and enforce hyperlinked developer attributions.

## Impact

- **Data Payload**: The `data/projects.json` file size will increase significantly to accommodate all 31k+ repositories.
- **Client Performance**: While initial data load takes slightly longer, the lazy-loading implementation will dramatically reduce DOM node count, keeping the page responsive.
- **User Experience**: Users can search the entirety of the community's output and easily navigate to developer profiles.

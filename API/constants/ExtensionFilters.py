default_ignore_dirs = {
    'node_modules', 'dist', 'build', '.git', '.svn', '.hg', '.idea', '.vscode', 
    '__pycache__', '.DS_Store', 'venv', 'env', '.next', '.nuxt', 'target', 
    '.terraform', '.gradle', 'logs', 'temp', 'tmp', 'out', '.pytest_cache', 
    'coverage', '.cache', '.expo', 'docs'

    # Static/Media/Public Assets
    'static', 'media', 'assets', 'public', 'resources', 'upload', 'downloads', 
    'images', 'fonts', 'icons', 'videos',  'vendor',

    # Framework-Specific (Laravel, Django, React, Vue, etc.)
    'storage', 'bootstrap/cache', 'public/storage', 'migrations', 
    '.env_backup', 'compiled', '__generated__', 
    '.vercel', '.parcel-cache', '.webpack-cache', '.storybook-static', 'contrib',
    
    # Database/Temp
    'db_data', 'database', 'dump', 'backups', 
    'uploads', 'temp_uploads', 'tmp_uploads',
}



default_ignore_extensions = {
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp3', '.mp4', '.avi', '.mov', 
    '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.log', '.sqlite', '.db', 
    '.exe', '.dll', '.class', '.jar', '.war', '.swp', '.iml', '.lock', '.bak', 
    '.iso', '.out', '.app', '.dmg', '.pkg', '.deb', '.rpm', '.msi', '.apk',
    '.json',  '.yaml', '.yml', '.toml', '.ini', '.properties', '.env',

    # Configuration Files
    '.env', '.cfg', '.config', '.ini', '.properties', '.toml', '.yaml', '.yml', 

    # Database Files
    '.sql', '.sqlite3', '.db-journal', '.psql', '.db-shm', '.db-wal', 

    # Web Assets (Minified/Bundled)
    '.min.js', '.min.css', '.bundle.js', '.map',

    # Certificates & Miscellaneous
    '.crt', '.pem', '.key', '.pid', '.sock', '.manifest'
}


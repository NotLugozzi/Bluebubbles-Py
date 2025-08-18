use glib::MainContext;
use once_cell::sync::Lazy;

pub static RUNTIME: Lazy<tokio::runtime::Runtime> = Lazy::new(|| {
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("Failed to build Tokio runtime")
});

pub fn spawn_async<F>(fut: F)
where
    F: std::future::Future<Output = ()> + Send + 'static,
{
    RUNTIME.spawn(fut);
}

pub fn glib_channel<T: Send + 'static>() -> (glib::Sender<T>, glib::Receiver<T>) {
    MainContext::channel(glib::Priority::default())
}

pub fn run_async_to_main<T, E, Fut>(fut: Fut) -> glib::Receiver<Result<T, E>>
where
    T: Send + 'static,
    E: Send + 'static,
    Fut: std::future::Future<Output = Result<T, E>> + Send + 'static,
{
    let (tx, rx) = glib_channel::<Result<T, E>>();
    spawn_async(async move {
        let res = fut.await;
        let _ = tx.send(res);
    });
    rx
}

pub fn normalize_url(input: &str) -> String {
    let trimmed = input.trim();
    if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
        trimmed.to_string()
    } else {
        format!("https://{}", trimmed)
    }
}

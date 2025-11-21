# authbooking/middleware.py

class DebugRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print("🔵 DebugRequestMiddleware INITIALIZED!")  # Harus muncul saat server start

    def __call__(self, request):
        # Print untuk SEMUA request ke /accounts/ (sesuaikan dengan URL kamu)
        if '/accounts/' in request.path:
            print("\n" + "🌐"*30)
            print(f"📍 PATH: {request.path}")
            print(f"📍 METHOD: {request.method}")
            print(f"📍 Content-Type: {request.content_type}")
            print(f"📍 POST: {dict(request.POST)}")
            try:
                print(f"📍 BODY: {request.body[:500]}")
            except:
                print(f"📍 BODY: (unable to read)")
            print("🌐"*30 + "\n")
        
        response = self.get_response(request)
        return response
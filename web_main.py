import asyncio
import pygame, sys, random
from collections import deque

# ---------- CONFIG ----------
GRID_SIZE = 10  # 10×10 grid
CELL_SIZE = 60  # pixels
WIDTH = HEIGHT = GRID_SIZE * CELL_SIZE

N_OBSTACLES = 16  # total wall tiles
MAX_CLUSTER_SIZE = 2  # longest cluster of connected walls
FLASH_TIME = 150  # ms for red wall flash
ERROR_TIME = 1000  # ms error message visible
AUTO_MOVE_DELAY = 300  # ms between auto moves

BACKGROUND = (255, 255, 255)
GRID_LINE = (200, 200, 200)
FLASH_COLOR = (255, 0, 0)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 150, 200)
BUTTON_TEXT = (255, 255, 255)

START_POS = (0, 0)

# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT + 80))  # Extra space for buttons
pygame.display.set_caption("Robot Grid - Arrow Keys + AUTO Mode")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 30)
button_font = pygame.font.SysFont(None, 24)

# --- create simple colored rectangles instead of loading images for web compatibility ---
robot_img = pygame.Surface((CELL_SIZE, CELL_SIZE))
robot_img.fill((50, 150, 250))  # Blue robot
pygame.draw.circle(robot_img, (255, 255, 255), (CELL_SIZE//2, CELL_SIZE//2), CELL_SIZE//3)

wall_img = pygame.Surface((CELL_SIZE, CELL_SIZE))
wall_img.fill((100, 100, 100))  # Gray wall
pygame.draw.rect(wall_img, (80, 80, 80), (5, 5, CELL_SIZE-10, CELL_SIZE-10))


# ---------- HELPERS ----------
def neighbors(x, y):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        yield x + dx, y + dy


def generate_obstacles():
    obstacles = set()

    def cluster_len(x, y):
        seen, stack = set(), [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in obstacles and (cx, cy) not in seen:
                seen.add((cx, cy))
                stack.extend([n for n in neighbors(cx, cy)])
        return len(seen)

    while len(obstacles) < N_OBSTACLES:
        x, y = random.randrange(GRID_SIZE), random.randrange(GRID_SIZE)
        if (x, y) == START_POS or (x, y) in obstacles:
            continue
        obstacles.add((x, y))
        if any(
                cluster_len(nx, ny) > MAX_CLUSTER_SIZE
                for nx, ny in neighbors(x, y) if (nx, ny) in obstacles):
            obstacles.remove((x, y))
    return obstacles


def find_path_bfs(start, goal, obstacles):
    """Find shortest path using BFS"""
    if start == goal:
        return []

    queue = deque([(start, [])])
    visited = {start}

    while queue:
        (x, y), path = queue.popleft()

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:  # down, right, up, left
            new_x, new_y = x + dx, y + dy

            if (0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE and
                (new_x, new_y) not in obstacles and (new_x, new_y) not in visited):

                new_path = path + [(dx, dy)]
                if (new_x, new_y) == goal:
                    return new_path

                queue.append(((new_x, new_y), new_path))
                visited.add((new_x, new_y))

    return []  # No path found


def get_random_goal(obstacles):
    """Get a random valid goal position"""
    while True:
        x, y = random.randrange(GRID_SIZE), random.randrange(GRID_SIZE)
        if (x, y) not in obstacles and (x, y) != START_POS:
            return (x, y)


def draw_button(text, x, y, width, height, is_hovered=False):
    """Draw a button and return its rect"""
    color = BUTTON_HOVER if is_hovered else BUTTON_COLOR
    button_rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, color, button_rect)
    pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)

    text_surf = button_font.render(text, True, BUTTON_TEXT)
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)

    return button_rect


def draw(obstacles, dog_pos, flash_wall=None, error_msg="", auto_mode=False, mouse_pos=None):
    screen.fill(BACKGROUND)

    # draw grid
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            pygame.draw.rect(
                screen, GRID_LINE,
                (col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

    # draw walls
    for (wx, wy) in obstacles:
        rect = (wx * CELL_SIZE, wy * CELL_SIZE)
        if flash_wall == (wx, wy):
            pygame.draw.rect(screen, FLASH_COLOR,
                             pygame.Rect(*rect, CELL_SIZE, CELL_SIZE))
        else:
            screen.blit(wall_img, rect)

    # draw robot
    screen.blit(robot_img, (dog_pos[0] * CELL_SIZE, dog_pos[1] * CELL_SIZE))

    # draw control buttons
    button_y = HEIGHT + 10
    button_width, button_height = 100, 30

    auto_button = draw_button(
        "AUTO ON" if auto_mode else "AUTO OFF",
        10, button_y, button_width, button_height,
        mouse_pos and pygame.Rect(10, button_y, button_width, button_height).collidepoint(mouse_pos)
    )

    reset_button = draw_button(
        "RESET (R)",
        120, button_y, button_width, button_height,
        mouse_pos and pygame.Rect(120, button_y, button_width, button_height).collidepoint(mouse_pos)
    )

    # draw instructions
    inst_text = "Arrow Keys: Manual Control | AUTO: Demo Mode"
    if auto_mode:
        inst_text = "AUTO MODE: Robot finding path automatically"

    text_surf = button_font.render(inst_text, True, (50, 50, 50))
    screen.blit(text_surf, (240, button_y + 5))

    # draw error popup (centered box)
    if error_msg:
        box_width, box_height = 400, 60
        box_x = (WIDTH - box_width) // 2
        box_y = (HEIGHT - box_height) // 2

        # background and red border
        pygame.draw.rect(screen, (255, 255, 255),
                         (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (255, 0, 0),
                         (box_x, box_y, box_width, box_height), 3)

        # center the text inside
        text = font.render(error_msg, True, (255, 0, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)

    pygame.display.flip()
    return auto_button, reset_button


# ---------- MAIN ----------
async def main():
    dog_x, dog_y = START_POS
    obstacles = generate_obstacles()

    flash_wall = None
    flash_timer = 0

    error_msg = ""
    error_timer = 0

    # AUTO mode variables
    auto_mode = False
    auto_timer = 0
    auto_path = []
    auto_goal = None

    running = True
    while running:
        dt = clock.tick(60)  # Increased FPS for smoother experience
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    auto_button, reset_button = draw(obstacles, (dog_x, dog_y), flash_wall, error_msg, auto_mode, mouse_pos)

                    if auto_button.collidepoint(mouse_pos):
                        auto_mode = not auto_mode
                        if auto_mode:
                            auto_goal = get_random_goal(obstacles)
                            auto_path = find_path_bfs((dog_x, dog_y), auto_goal, obstacles)
                            auto_timer = 0
                        else:
                            auto_path = []
                            auto_goal = None
                    elif reset_button.collidepoint(mouse_pos):
                        dog_x, dog_y = START_POS
                        obstacles = generate_obstacles()
                        error_msg = ""
                        flash_wall = None
                        auto_path = []
                        auto_goal = None
                        if auto_mode:
                            auto_goal = get_random_goal(obstacles)
                            auto_path = find_path_bfs((dog_x, dog_y), auto_goal, obstacles)

        # Movement logic
        dx = dy = 0

        if auto_mode:
            # AUTO movement
            auto_timer += dt
            if auto_timer >= AUTO_MOVE_DELAY and auto_path:
                dx, dy = auto_path.pop(0)
                auto_timer = 0

                # If reached goal or path is empty, find new goal
                if not auto_path or (dog_x + dx, dog_y + dy) == auto_goal:
                    auto_goal = get_random_goal(obstacles)
                    auto_path = find_path_bfs((dog_x + dx, dog_y + dy), auto_goal, obstacles)
        else:
            # Manual movement with arrow keys
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]: dy = -1
            if keys[pygame.K_DOWN]: dy = 1
            if keys[pygame.K_LEFT]: dx = -1
            if keys[pygame.K_RIGHT]: dx = 1

        # Reset functionality
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:  # reset robot & regenerate obstacles
            dog_x, dog_y = START_POS
            obstacles = generate_obstacles()
            error_msg = ""
            flash_wall = None
            auto_path = []
            auto_goal = None
            if auto_mode:
                auto_goal = get_random_goal(obstacles)
                auto_path = find_path_bfs((dog_x, dog_y), auto_goal, obstacles)

        # try to move
        new_x, new_y = dog_x + dx, dog_y + dy
        if (dx or dy) and 0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE:
            if (new_x, new_y) not in obstacles:
                dog_x, dog_y = new_x, new_y
            else:
                flash_wall = (new_x, new_y)
                flash_timer = FLASH_TIME
                error_msg = "❌ Wall hit! Change direction"
                error_timer = ERROR_TIME
                # In auto mode, find new path if blocked
                if auto_mode:
                    auto_goal = get_random_goal(obstacles)
                    auto_path = find_path_bfs((dog_x, dog_y), auto_goal, obstacles)

        # update timers
        if flash_timer > 0:
            flash_timer -= dt
            if flash_timer <= 0:
                flash_wall = None
        if error_timer > 0:
            error_timer -= dt
            if error_timer <= 0:
                error_msg = ""

        draw(obstacles, (dog_x, dog_y), flash_wall, error_msg, auto_mode, mouse_pos)
        await asyncio.sleep(0)  # Allow browser to update

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
